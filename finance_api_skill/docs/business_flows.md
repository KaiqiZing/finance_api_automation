# 业务流程

## System 模块范围

当前 system 模块面向 RuoYi 后端，覆盖以下资源：

- 登录与当前用户信息。
- 用户管理。
- 角色管理。
- 岗位管理。
- 部门管理。
- 通知公告。
- RBAC 与无 Token 鉴权回归。

关键接口类：

- `SystemLoginAPI`
- `SystemUserAPI`
- `SystemRoleAPI`
- `SystemPostAPI`
- `SystemDeptAPI`
- `SystemNoticeAPI`

## 基础认证流程

```text
SystemLoginAPI.login()
  -> POST /auth/login
  -> 返回 data.access_token
  -> api.set_token(token)
  -> 后续请求携带 Authorization: Bearer <token>
```

`business/system_flows.py` 提供了标准链路：

```text
login_and_get_info()
  -> do_login()
  -> do_get_info()
```

成功后写入 `GlobalContext`：

- `system_token`
- `system_username`
- `system_user_id`
- `system_user_name`
- `system_roles`
- `system_permissions`

## 端到端业务流

核心文件：

- `tests/test_system/test_system_business_flows.py`

该文件实现 `TC-SYS-BIZ-001` 到 `TC-SYS-BIZ-010`。

### BIZ-001 用户完整生命周期

链路：

```text
登录
  -> 新增岗位
  -> 新增角色
  -> 选择三级部门
  -> 新增用户并绑定 dept/role/post
  -> DB 校验 sys_user_role 和 sys_user_post
  -> 修改用户昵称
  -> DB 校验 nick_name
  -> 删除用户
  -> DB 校验 del_flag='2'
```

重点：

- 用户名、岗位编码、角色 key 使用 UUID 短串保证唯一。
- 删除用户后若依通常是逻辑删除，`del_flag='2'`。
- finally 中按用户、角色、岗位顺序兜底清理。

### BIZ-002 角色授权闭环

链路：

```text
新增角色
  -> 新增用户并绑定角色
  -> DB 校验 sys_user_role 存在
  -> allocatedList 应能查到用户
  -> update_user(role_ids=[]) 去除角色
  -> DB 校验 sys_user_role 消失
  -> unallocatedList 应能查到用户
```

重点：

- 授权状态不只看接口返回，还要查关联表。
- 去授权通过更新用户 `role_ids=[]` 完成。

### BIZ-003 岗位授权闭环

链路：

```text
新增岗位
  -> 新增角色
  -> 新增用户并绑定岗位
  -> DB 校验 sys_user_post 存在
  -> update_user(post_ids=[]) 解绑岗位
  -> DB 校验 sys_user_post 消失
  -> 删除岗位成功
```

重点：

- 删除岗位前必须先解除用户占用。
- 岗位关联以 `sys_user_post` 为最终断言。

### BIZ-004 角色删除保护

链路：

```text
新增岗位与角色
  -> 新增用户绑定角色
  -> 删除角色预期失败
  -> msg 包含已分配或不能删除
  -> DB 校验关联仍存在
  -> 删除用户并 purge 关联
  -> 再次删除角色成功
```

重点：

- 这是业务约束用例，不是接口成功用例。
- 第一次删除返回 `code=500` 属于预期结果。

### BIZ-005 岗位删除保护

链路：

```text
新增岗位与角色
  -> 新增用户绑定岗位
  -> 删除岗位预期失败
  -> msg 包含已分配或不能删除
  -> DB 校验岗位关联仍存在
  -> 删除用户并 purge 关联
  -> 再次删除岗位成功
```

重点：

- 与角色删除保护类似。
- 断言重点是占用状态下不可删除，以及清理占用后可删除。

### BIZ-006 角色状态影响

链路：

```text
新增角色并绑定用户
  -> change_status(status='1') 停用
  -> DB 校验 sys_role.status='1'
  -> 详情接口状态一致
  -> allocatedList 仍可查询
  -> change_status(status='0') 恢复
  -> DB 校验 sys_role.status='0'
```

重点：

- 停用角色不等同于删除授权关系。
- 状态最终以 DB 字段为准。

### BIZ-007 数据权限切换稳定性

链路：

```text
新增角色
  -> 依次切换 dataScope=1/2/3/4/5
  -> 每次切换后 DB 校验 data_scope
  -> 最终态应为 data_scope='5'
```

重点：

- 连续写入验证稳定性。
- 每次切换后都查 DB，避免只验证最后一次。

### BIZ-008 组织树与用户归属联动

链路：

```text
新增角色
  -> 新增父部门
  -> 新增子部门
  -> 在子部门新增用户
  -> 删除子部门预期失败
  -> 更新用户归属到父部门
  -> 删除子部门成功
  -> 删除父部门预期失败
  -> 删除用户
  -> 删除父部门成功
```

重点：

- 部门删除受用户归属影响。
- 用户迁移后要 DB 校验 `dept_id`。
- 清理顺序为用户、子部门、父部门、角色。

### BIZ-009 公告发布全链路

链路：

```text
新增公告
  -> 列表按标题命中
  -> 列表按状态过滤命中
  -> 修改标题、内容、状态
  -> 详情校验字段一致
  -> 删除公告
  -> DB 校验记录不存在
```

重点：

- 公告删除后 DB 应不存在。
- 列表与详情都要覆盖，避免只测 CRUD 返回码。

### BIZ-010 鉴权统一防护回归

链路：

```text
不注入 token
  -> 用户写接口
  -> 角色写接口
  -> 岗位写接口
  -> 部门写接口
  -> 公告写接口
  -> 全部应 code != 200
```

重点：

- 创建无 token API 实例，不调用 `set_token()`。
- 不同环境鉴权提示可能不同，底线断言是 `code != 200`。
- 若响应有 msg，可检查认证、token、401、unauthorized 等关键词。

## 用例编写模板

```python
def test_xxx_business_flow(self) -> None:
    token = _login_and_get_token()
    user_api, role_api, post_api, dept_api, notice_api = _setup_apis(token)

    created_id = None
    try:
        with allure.step("准备前置数据"):
            ...

        with allure.step("执行业务动作"):
            ...

        with allure.step("DB 校验最终态"):
            ...

    finally:
        # 逆序清理，失败也不能污染环境
        ...
```

## 清理策略

- 用户：优先调用删除接口，再调用 `purge_sys_user_bindings(user_id)` 清理残留绑定。
- 角色：调用 `delete_roles([role_id])`。
- 岗位：调用 `delete_posts([post_id])`。
- 部门：先删子部门，再删父部门。
- 公告：调用 `delete_notices([notice_id])`。

## 排障路径

1. 看失败断言属于接口返回、DB 状态还是清理异常。
2. 在 Allure 中查看该 step 的响应附件和 DB 附件。
3. 找到失败时附加的 `last_trace_id`。
4. 用 Mongo 查询 API 日志，或查看 JSONL 降级日志。
5. 针对 `ry_cloud` 的 `sys_user`、`sys_role`、`sys_post`、`sys_dept`、`sys_notice`、关联表做回查。

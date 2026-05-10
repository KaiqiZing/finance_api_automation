# 测试用例格式与 @allure 注解风格规范

本文档基于 `tests/test_system/` 下已有用例（`test_add_user.py`、`test_delete_user.py`、`test_batch_add_data.py` 等）整理，作为大模型生成新用例时的强制对齐标准。

---

## 一、文件头注释规范

每个测试文件必须以三引号 docstring 开头，包含以下三段：

```python
"""
{资源}管理 测试用例。

真实接口:
    {HTTP方法}  {完整接口路径，含 host}
               请求头: Authorization: Bearer <access_token>
               请求体/路径参数: {字段说明}
               响应体: {"code": 200, "msg": "操作成功"}

用例清单:
    TC-SYS-{CODE}-001  {用例一句话描述}，断言 {核心断言}
    TC-SYS-{CODE}-002  ...
"""
```

规则：

- `真实接口` 段写清 HTTP 方法、含端口的完整路径、请求头、请求/响应结构摘要。
- `用例清单` 段罗列所有用例编号和一句话描述，与类内实际用例一一对应。
- 不要在文件头写实现细节，只写接口契约摘要。

---

## 二、导入顺序

```python
from __future__ import annotations  # 必须第一行

import uuid                          # 标准库

import allure                        # 第三方
import pytest

from api.system.xxx_api import SystemXxxAPI          # 本项目
from tests.test_system.conftest import _login_and_get_token, gen_username
from utils.db_client import DBClient
from utils.logger import logger
from utils.system_ruoyi_queries import fetch_xxx_id_by_xxx
```

规则：

- `from __future__ import annotations` 固定第一行。
- 导入块顺序：标准库 → 第三方 → 本项目，组间空一行。
- 不要 `import *`，不要在用例内部做条件导入。

---

## 三、辅助函数区

文件内辅助函数写在导入块之后、测试类之前，并用分隔注释标注区域。

```python
# ==============================================================================
# 辅助函数
# ==============================================================================

def _get_xxx_id_by_name(name: str) -> int | None:
    """从 sys_xxx 表按名称查询 id。"""
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT xxx_id FROM sys_xxx WHERE xxx_name = %s AND del_flag = '0' LIMIT 1",
        (name,),
    )
    return int(row["xxx_id"]) if row else None


def _gen_xxx_name() -> str:
    return "自动化{资源}_" + uuid.uuid4().hex[:8]
```

规则：

- 辅助函数命名以单下划线 `_` 开头，表示模块内使用。
- 生成唯一名称的函数统一用 `uuid.uuid4().hex[:N]` 保证并发安全。
- 复杂 SQL 查询辅助优先沉淀到 `utils/system_ruoyi_queries.py`，本文件只保留测试专属辅助。

---

## 四、测试类结构

### 4.1 类级 @allure 装饰器

```python
# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("{资源中文名}")
class Test{Resource}{Action}:
    """{资源中文名} {动作} 接口 {HTTP方法} /system/{resource} 测试集合。"""
```

装饰器层级对照表：

| 装饰器 | 含义 | 示例值 |
| --- | --- | --- |
| `@allure.epic` | 业务大模块 | `"系统管理模块"` |
| `@allure.feature` | 资源/功能域 | `"用户管理"` / `"角色管理"` |
| `@allure.story` | 用例场景分组 | `"正常新增用户"` / `"鉴权异常拦截"` |
| `@allure.title` | 用例唯一标题 | `"TC-SYS-USR-001：仅传必填字段新增用户成功"` |
| `@allure.severity` | 优先级 | 见下表 |

严重级别选择规范：

| 值 | 使用场景 |
| --- | --- |
| `BLOCKER` | 核心正向链路（如首个必填字段新增、先增后删完整链路） |
| `CRITICAL` | 鉴权拦截、唯一字段冲突拦截 |
| `NORMAL` | 数据驱动枚举覆盖、组合矩阵、可选字段边界 |
| `MINOR` | 软删/逻辑校验、次要异常场景 |

### 4.2 单用例方法结构

```python
    # ==================================================================
    # TC-SYS-{CODE}-001：{用例标题}
    # ==================================================================

    @allure.story("{场景分组}")
    @allure.title("TC-SYS-{CODE}-001：{完整用例标题}")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke   # 仅冒烟用例加此标记
    def test_{action}_{scenario}(self) -> None:
        """
        {一到两句话描述前置条件和核心断言}:
        - 断言1
        - 断言2
        """
        token = _login_and_get_token()
        api = System{Resource}API()
        api.set_token(token)

        # 前置数据准备（带 allure.step）
        with allure.step("..."):
            ...

        # 核心操作（带 allure.step）
        with allure.step("..."):
            resp = api.{method}(...)

        # 附件
        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="{ResourceAction} Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        # 断言（每条断言独立一个 allure.step）
        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"期望 200，实际 code={resp.get('code')}, msg={resp.get('msg')}"
            )
```

---

## 五、@allure.step 使用规范

### 5.1 何时必须用 with allure.step

- 每一条 **核心断言** 独占一个 step，step 描述即断言目标。
- 接口调用本身必须包裹在 step 中，描述"调用接口 + 关键参数摘要"。
- DB 查询/回查必须包裹在 step 中，描述"从 xxx 表查询 xxx"。
- 附加 Allure 附件时需用 step 包裹（便于在报告里收起/展开）。

### 5.2 step 描述命名规范

```python
# 接口调用
with allure.step(f"调用新增接口（仅必填字段）: userName={username}"):

# DB 查询
with allure.step("从 sys_user 表查询已存在的 user_name"):

# 断言
with allure.step("断言 code == 200"):
with allure.step('断言 msg 含"登录账号已存在"'):
with allure.step(f"断言 code == 200（性别: {sex_label}）"):

# 附件
with allure.step("附加完整响应"):
with allure.step("附加删除响应"):
```

---

## 六、allure.attach 附件规范

### 6.1 TEXT 附件（响应体、参数摘要）

```python
allure.attach(
    body=str(resp),
    name="AddUser Response",
    attachment_type=allure.attachment_type.TEXT,
)

allure.attach(
    body=(
        f"userName={username}\n"
        f"dept_id={dept_id}\n"
        f"code={resp.get('code')}\n"
        f"msg={resp.get('msg')}"
    ),
    name="DB 取数结果",
    attachment_type=allure.attachment_type.TEXT,
)
```

### 6.2 JSON 附件（DB 回查、结构化数据）

```python
import json

def _attach_json(name: str, data: Any) -> None:
    allure.attach(
        body=json.dumps(data, ensure_ascii=False, indent=2, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )
```

### 6.3 附件命名规范

- 格式：`{Resource}{Action} Response` / `DB 查询结果` / `DB 回查结果`
- 含参数驱动时加参数标识：`f"性别 [{sex_label}] 新增结果"`
- 不要把 token、password、手机号、身份证写入附件明文。

---

## 七、断言规范

### 7.1 正向断言

```python
assert resp.get("code") == 200, (
    f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
)
assert resp.get("msg") == "操作成功", (
    f"msg 异常: {resp.get('msg')!r}"
)
```

### 7.2 异常场景断言

```python
# 业务互斥
assert resp.get("code") == 500, (
    f"期望 500，实际 code={resp.get('code')}, msg={resp.get('msg')}"
)
assert "登录账号已存在" in resp.get("msg", ""), (
    f"msg 不含预期提示，实际: {resp.get('msg')!r}"
)

# 鉴权拦截（关键词匹配）
assert resp.get("code") != 200, (
    f"未带 token 竟返回 200！响应: {resp}"
)
msg = str(resp.get("msg", ""))
keywords = ["令牌", "token", "认证", "登录", "未授权", "过期", "expire"]
matched = any(kw.lower() in msg.lower() for kw in keywords)
assert matched, (
    f"msg 未包含鉴权提示关键词，实际 msg: {msg!r}，期望之一: {keywords}"
)
```

### 7.3 DB 最终态断言

```python
# 软删验证（RuoYi del_flag='2'）
assert after_row is not None, (
    f"DB 中已找不到 user_id={target_id} 的记录"
)
assert actual_flag == "2", (
    f"期望 del_flag='2'，实际={actual_flag!r}，user_id={target_id}"
)
```

断言消息规则：

- 必须包含实际值（`code`/`msg`/`flag`），方便失败时一眼定位。
- 使用 `!r` 输出字符串原始表示，以区分空字符串和 None。
- 不要写 `assert True` 或无消息的裸 `assert`。

---

## 八、try/finally 数据清理规范

所有会创建真实数据的用例必须使用 `try/finally` 保证清理：

```python
def test_add_{resource}_xxx(self) -> None:
    token = _login_and_get_token()
    api = System{Resource}API()
    api.set_token(token)

    name = _gen_{resource}_name()
    {resource}_id: int | None = None

    try:
        with allure.step("新增{资源}"):
            resp = api.add_{resource}(name=name)
        assert resp.get("code") == 200, f"新增失败: {resp}"

        {resource}_id = fetch_{resource}_id_by_{field}(name)
        assert {resource}_id is not None, "新增后 DB 未查到 ID"

    finally:
        if {resource}_id is not None:
            api.set_token(token)
            api.delete_{resources}([{resource}_id])
```

规则：

- `finally` 内不要再调用 `assert`，只做清理。
- 清理顺序遵循依赖关系：先删关联表（如用户-角色），再删主表（如角色）。
- 清理失败只打 `logger.warning`，不让清理异常掩盖原始用例失败。

---

## 九、数据驱动用例规范（@pytest.mark.parametrize）

### 9.1 简单参数驱动

```python
@allure.story("正常新增用户")
@allure.title("TC-SYS-USR-008：数据驱动 - sex 枚举 0/1/2 均可新增用户成功")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("sex,sex_label", [
    ("0", "男"),
    ("1", "女"),
    ("2", "未知"),
])
def test_add_{resource}_different_{field}(self, sex: str, sex_label: str) -> None:
    """数据驱动：对 {field} 枚举每个值各新增一个实体，均断言 code==200。"""
```

### 9.2 动态标题（多维组合）

当 `@pytest.mark.parametrize` 组合较多时，用 `allure.dynamic.title` 在运行时构造标题：

```python
@pytest.mark.parametrize("role_mode", ["none", "partial", "all"])
@pytest.mark.parametrize("post_mode", ["none", "partial", "all"])
def test_add_user_role_post_selection_matrix(self, role_mode: str, post_mode: str) -> None:
    allure.dynamic.title(
        "TC-SYS-USR-009：roleIds/postIds — "
        f"role={role_mode}, post={post_mode}，断言 code==200"
    )
```

### 9.3 前置数据不足时 skip

```python
if role_mode == "all" and not all_roles:
    pytest.skip("sys_role 无可用普通角色，无法测「全选」角色")
```

`pytest.skip()` 仅在 **环境前置数据缺失** 时使用，不可掩盖真实失败。

---

## 十、logger 使用规范

测试用例中的 logger 调用遵循以下分级：

```python
from utils.logger import logger

# 前置步骤开始
logger.info("[DEL-001] 前置步骤：新增测试用户 userName={}", username)

# 调试信息（中间状态、响应体）
logger.debug("[DEL-001] 新增响应: {}", add_resp)
logger.debug("[DEL-001] 查询 sys_user 获取 user_id，userName={}", username)

# 关键结果（ID 确认、操作成功）
logger.info("[DEL-001] 用户新增成功，userName={}", username)
logger.info("[DEL-001] 查到 user_id={}，userName={}", user_id, username)

# 高风险操作（删除、修改状态）
logger.warning("[DEL-001] 即将删除用户 | user_id={} | userName={}", user_id, username)

# 预期异常确认
logger.info("[DEL-003] 按预期被拦截 | user_id={} | code={} | msg={}",
            nonexistent_id, resp.get("code"), resp.get("msg"))

# DB 未查到数据（影响用例继续执行）
logger.error("[DEL-001] DB 中未找到用户 {}，无法执行删除", username)
```

规则：

- 前缀格式：`[{TC编号}]`，便于按用例过滤日志。
- 使用 loguru 的 `{}` 占位符，不用 `%s` 或 f-string 拼接（避免日志级别未达到时也做字符串构建）。
- 高风险写操作（delete/update）必须用 `logger.warning`。
- 不在 `finally` 清理块里调用 `logger.error`（清理失败只打 warning）。

---

## 十一、用例编号体系

| 前缀 | 资源 | 示例 |
| --- | --- | --- |
| `TC-SYS-USR` | 用户管理 | `TC-SYS-USR-001` |
| `TC-SYS-ROLE` | 角色管理 | `TC-SYS-ROLE-001` |
| `TC-SYS-POST` | 岗位管理 | `TC-SYS-POST-001` |
| `TC-SYS-DEPT` | 部门管理 | `TC-SYS-DEPT-001` |
| `TC-SYS-NTC` | 公告管理 | `TC-SYS-NTC-001` |
| `TC-SYS-BIZ` | 业务流 | `TC-SYS-BIZ-001` |
| `TC-SYS-DEL` | 删除专项 | `TC-SYS-DEL-001` |
| `TC-BATCH` | 批量新增 | `TC-BATCH-001` |

---

## 十二、完整用例参考对照

以下摘自 `tests/test_system/test_delete_user.py`，展示正向主链路 BLOCKER 用例的完整结构：

```python
@allure.story("正常删除用户")
@allure.title("TC-SYS-DEL-001：先新增用户再删除，断言 code==200")
@allure.severity(allure.severity_level.BLOCKER)
@pytest.mark.smoke
def test_delete_user_after_add(self) -> None:
    """
    完整正向链路：
    1. 新增一个测试用户；
    2. 从 sys_user 表查出该用户的 user_id；
    3. 调用删除接口，断言 code==200。
    """
    token = _login_and_get_token()
    user_api = SystemUserAPI()
    user_api.set_token(token)
    username = gen_username()

    with allure.step(f"新增测试用户: userName={username}"):
        logger.info("[DEL-001] 前置步骤：新增测试用户 userName={}", username)
        add_resp = user_api.add_user(
            user_name=username,
            nick_name="删除链路测试",
            password="Test@123456",
        )
        assert add_resp.get("code") == 200, f"前置新增失败: {add_resp}"

    with allure.step(f"从 sys_user 表查询 {username} 的 user_id"):
        user_id = _get_user_id_by_name(username)
        if user_id is None:
            pytest.fail(f"新增后在 sys_user 中未找到用户 {username}")

    allure.attach(
        body=f"userName={username}\nuser_id={user_id}",
        name="新增用户信息",
        attachment_type=allure.attachment_type.TEXT,
    )

    with allure.step(f"调用删除接口 DELETE /system/user/{user_id}"):
        logger.warning("[DEL-001] 即将删除用户 | user_id={} | userName={}", user_id, username)
        del_resp = user_api.delete_user(user_id)

    with allure.step("附加删除响应"):
        allure.attach(
            body=str(del_resp),
            name="DeleteUser Response",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("断言 code == 200"):
        assert del_resp.get("code") == 200, (
            f"删除失败: code={del_resp.get('code')}, msg={del_resp.get('msg')}"
        )

    with allure.step("断言 msg == '操作成功'"):
        assert del_resp.get("msg") == "操作成功", (
            f"msg 异常: {del_resp.get('msg')!r}"
        )
```

---

## 十三、生成新用例检查清单

生成前必须确认：

- [ ] 文件头注释包含接口契约摘要和用例清单。
- [ ] 类装饰器：`@allure.epic` + `@allure.feature` 已就位。
- [ ] 每个用例方法有 `@allure.story` + `@allure.title`（含 TC 编号）+ `@allure.severity`。
- [ ] 核心断言每条独立一个 `with allure.step`。
- [ ] 接口调用包裹在 `with allure.step` 中，描述含关键参数。
- [ ] 响应体已通过 `allure.attach` 附加为 TEXT 附件。
- [ ] 创建实体的用例已用 `try/finally` 清理。
- [ ] `pytest.skip()` 仅用于前置数据缺失，不掩盖真实失败。
- [ ] 高风险操作调用了 `logger.warning`。
- [ ] 断言消息含实际值，便于失败排查。
- [ ] 敏感字段（密码、手机、身份证）未明文写入附件。

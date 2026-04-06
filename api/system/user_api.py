"""
SystemUserAPI：系统用户相关接口（RuoYi 后端）。

接口列表:
    GET    /dev-api/system/user/getInfo  查询当前登录用户信息
    POST   /dev-api/system/user          新增系统用户
    PUT    /dev-api/system/user          修改系统用户
    DELETE /dev-api/system/user/{id}     删除系统用户（支持批量，逗号分隔）

模板目录: data/templates/system/
依赖: Authorization: Bearer <token>（通过 set_token() 注入）

getInfo 响应示例:
    {
        "code": 200,
        "msg": "操作成功",
        "user": {
            "userId": 1,
            "userName": "admin",
            "nickName": "若依",
            "email": "ry@163.com",
            "phonenumber": "15888888888",
            "sex": "1",
            "status": "0"
        },
        "roles": ["admin"],
        "permissions": ["*:*:*"]
    }

add_user 响应示例:
    成功: {"code": 200, "msg": "操作成功"}
    失败: {"code": 500, "msg": "新增用户'xxx'失败，登录账号已存在"}

update_user 响应示例:
    成功: {"code": 200, "msg": "操作成功"}
    失败(邮箱重复): {"code": 500, "msg": "修改用户'xxx'失败，邮箱账号已存在"}
    失败(手机重复): {"code": 500, "msg": "修改用户'xxx'失败，手机号码已存在"}

delete_user 响应示例:
    成功: {"code": 200, "msg": "操作成功"}
    失败: {"code": 500, "msg": "..."}
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI
from config.settings import cfg
from core.request_wrapper import RequestConfig, RequestWrapper


class SystemUserAPI(BaseAPI):
    """系统用户接口，需先注入 Token 才能请求。"""

    _MODULE = "system"
    _TEMPLATE = "get_info"

    def __init__(self) -> None:
        sys_cfg = cfg.get("system_api", {})
        wrapper = RequestWrapper(
            base_url=sys_cfg.get("base_url", "http://localhost:1024/dev-api"),
            config=RequestConfig(
                timeout=sys_cfg.get("timeout", 15),
                verify_ssl=sys_cfg.get("verify_ssl", False),
            ),
        )
        super().__init__(wrapper=wrapper)

    def get_info(self) -> dict[str, Any]:
        """
        查询当前登录用户的详细信息（权限列表、角色列表、用户基本信息）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Returns:
            响应 body，包含 ``user``、``roles``、``permissions`` 字段。
        """
        return self._wrapper.get("/system/user/getInfo")

    def add_user(
        self,
        user_name: str | None = None,
        nick_name: str | None = None,
        password: str | None = None,
        phonenumber: str | None = None,
        email: str | None = None,
        sex: str | None = None,
        status: str | None = None,
        dept_id: int | None = None,
        role_ids: list[int] | None = None,
        post_ids: list[int] | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """
        新增系统用户。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            user_name:   用户名（唯一，必填；不传则由模板随机生成）。
            nick_name:   昵称（必填；不传则由模板随机生成）。
            password:    明文密码（必填；不传则使用模板默认值 Test@123456）。
            phonenumber: 手机号（11 位）。
            email:       邮箱。
            sex:         性别，"0" 男 / "1" 女 / "2" 未知。
            status:      状态，"0" 正常 / "1" 停用，默认 "0"。
            dept_id:     部门 ID（103 研发/104 市场/105 测试/106 财务/107 运维）。
            role_ids:    角色 ID 数组，默认 [2]。
            post_ids:    岗位 ID 数组（1 董事长/2 项目经理/3 人力资源/4 普通员工）。
            remark:      备注。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {}
        if user_name is not None:
            overrides["payload.userName"] = user_name
        if nick_name is not None:
            overrides["payload.nickName"] = nick_name
        if password is not None:
            overrides["payload.password"] = password
        if phonenumber is not None:
            overrides["payload.phonenumber"] = phonenumber
        if email is not None:
            overrides["payload.email"] = email
        if sex is not None:
            overrides["payload.sex"] = sex
        if status is not None:
            overrides["payload.status"] = status
        if dept_id is not None:
            overrides["payload.deptId"] = dept_id
        if role_ids is not None:
            overrides["payload.roleIds"] = role_ids
        if post_ids is not None:
            overrides["payload.postIds"] = post_ids
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "add_user", overrides or None)
        return self._wrapper.post("/system/user", json=payload)

    def update_user(
        self,
        user_id: int,
        dept_id: int,
        user_name: str,
        nick_name: str | None = None,
        email: str | None = None,
        phonenumber: str | None = None,
        sex: str | None = None,
        status: str | None = None,
        role_ids: list[int] | None = None,
        post_ids: list[int] | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """
        修改系统用户。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。
        注意: userId/deptId/userName 须先从 DB 查询后再传入，不可凭空构造。
              若依服务端校验 userName 不能为空，即使不修改用户名也必须携带原值。

        Args:
            user_id:     必填，目标用户 ID。
            dept_id:     必填，用户所在部门 ID（须与 DB 中一致）。
            user_name:   必填，用户登录账号（即使不修改也必须传原值）。
            nick_name:   昵称。
            email:       邮箱（修改时会检查唯一性）。
            phonenumber: 手机号（修改时会检查唯一性）。
            sex:         性别，"0" 男 / "1" 女 / "2" 未知。
            status:      状态，"0" 正常 / "1" 停用。
            role_ids:    角色 ID 数组。
            post_ids:    岗位 ID 数组。
            remark:      备注。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {
            "payload.userId": user_id,
            "payload.deptId": dept_id,
            "payload.userName": user_name,
        }
        if nick_name is not None:
            overrides["payload.nickName"] = nick_name
        if email is not None:
            overrides["payload.email"] = email
        if phonenumber is not None:
            overrides["payload.phonenumber"] = phonenumber
        if sex is not None:
            overrides["payload.sex"] = sex
        if status is not None:
            overrides["payload.status"] = status
        if role_ids is not None:
            overrides["payload.roleIds"] = role_ids
        if post_ids is not None:
            overrides["payload.postIds"] = post_ids
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "update_user", overrides)
        return self._wrapper.put("/system/user", json=payload)

    def delete_user(self, user_id: int) -> dict[str, Any]:
        """
        删除系统用户。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            user_id: 要删除的用户 ID（对应 sys_user.user_id，须 >= 3，
                     避免误删 admin 等内置账号）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        return self._wrapper.delete(f"/system/user/{user_id}")

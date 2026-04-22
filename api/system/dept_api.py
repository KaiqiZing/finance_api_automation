"""
SystemDeptAPI：系统部门相关接口（RuoYi 后端）。

接口列表:
    GET    /system/dept/list           获取部门列表（权限: system:dept:list）
    POST   /system/dept                新增部门（权限: system:dept:add）
    PUT    /system/dept                修改部门（权限: system:dept:edit）
    GET    /system/dept/{deptId}       获取部门详情（权限: system:dept:query）
    DELETE /system/dept/{deptId}       删除部门（权限: system:dept:remove）

模板目录: data/templates/system/
    POST body → add_dept.yaml
    PUT  body → update_dept.yaml

依赖: Authorization: Bearer <token>（通过 set_token() 注入）

add_dept 响应示例:
    成功: {"code": 200, "msg": "操作成功"}
    失败(deptName 重复): {"code": 500, "msg": "新增部门'xxx'失败，部门名称已存在"}

list_depts 响应示例:
    {
        "code": 200,
        "msg": "查询成功",
        "data": [{"deptId": 100, "deptName": "若依科技", ...}]
    }
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI
from config.settings import cfg
from core.request_wrapper import RequestConfig, RequestWrapper


class SystemDeptAPI(BaseAPI):
    """系统部门接口，需先注入 Token 才能请求。"""

    _MODULE = "system"

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

    # ------------------------------------------------------------------
    # 4.1 获取部门列表
    # ------------------------------------------------------------------

    def list_depts(
        self,
        dept_name: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        获取部门列表（支持按名称模糊查询和状态筛选）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            dept_name: 部门名称（模糊查询，不传则返回全量）。
            status:    部门状态，"0" 正常 / "1" 停用。

        Returns:
            响应 body，包含 ``data`` 字段（部门树列表）。
        """
        params: dict[str, Any] = {}
        if dept_name is not None:
            params["deptName"] = dept_name
        if status is not None:
            params["status"] = status
        return self._wrapper.get("/system/dept/list", params=params or None)

    # ------------------------------------------------------------------
    # 4.2 新增部门
    # ------------------------------------------------------------------

    def add_dept(
        self,
        parent_id: int | None = None,
        dept_name: str | None = None,
        order_num: int | None = None,
        leader: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        status: str | None = None,
        ancestors: str | None = None,
    ) -> dict[str, Any]:
        """
        新增部门。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            parent_id: 父部门 ID（必填；不传则由模板默认值 100）。
            dept_name: 部门名称（必填；不传则由模板随机生成）。
            order_num: 显示顺序（必填；不传则由模板默认值 999）。
            leader:    负责人（可选）。
            phone:     联系电话（可选，11 位）。
            email:     邮箱（可选，50 字符以内）。
            status:    部门状态，"0" 正常 / "1" 停用（可选，默认 "0"）。
            ancestors: 祖级列表（可选，格式如 "0,100"）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {}
        if parent_id is not None:
            overrides["payload.parentId"] = parent_id
        if dept_name is not None:
            overrides["payload.deptName"] = dept_name
        if order_num is not None:
            overrides["payload.orderNum"] = order_num
        if leader is not None:
            overrides["payload.leader"] = leader
        if phone is not None:
            overrides["payload.phone"] = phone
        if email is not None:
            overrides["payload.email"] = email
        if status is not None:
            overrides["payload.status"] = status
        if ancestors is not None:
            overrides["payload.ancestors"] = ancestors

        payload = self._build_payload(self._MODULE, "add_dept", overrides or None)
        return self._wrapper.post("/system/dept", json=payload)

    # ------------------------------------------------------------------
    # 4.3 修改部门
    # ------------------------------------------------------------------

    def update_dept(
        self,
        dept_id: int,
        parent_id: int,
        dept_name: str,
        order_num: int,
        leader: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        status: str | None = None,
        ancestors: str | None = None,
    ) -> dict[str, Any]:
        """
        修改部门。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            dept_id:   部门 ID（必填）。
            parent_id: 父部门 ID（必填）。
            dept_name: 部门名称（必填）。
            order_num: 显示顺序（必填）。
            leader:    负责人（可选）。
            phone:     联系电话（可选）。
            email:     邮箱（可选）。
            status:    部门状态，"0" 正常 / "1" 停用（可选）。
            ancestors: 祖级列表（可选）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {
            "payload.deptId": dept_id,
            "payload.parentId": parent_id,
            "payload.deptName": dept_name,
            "payload.orderNum": order_num,
        }
        if leader is not None:
            overrides["payload.leader"] = leader
        if phone is not None:
            overrides["payload.phone"] = phone
        if email is not None:
            overrides["payload.email"] = email
        if status is not None:
            overrides["payload.status"] = status
        if ancestors is not None:
            overrides["payload.ancestors"] = ancestors

        payload = self._build_payload(self._MODULE, "update_dept", overrides)
        return self._wrapper.put("/system/dept", json=payload)

    # ------------------------------------------------------------------
    # 4.4 获取部门详情
    # ------------------------------------------------------------------

    def get_dept(self, dept_id: int) -> dict[str, Any]:
        """
        获取部门详情。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            dept_id: 部门 ID（来自 sys_dept.dept_id）。

        Returns:
            响应 body，包含部门完整信息。
        """
        return self._wrapper.get(f"/system/dept/{dept_id}")

    # ------------------------------------------------------------------
    # 4.5 删除部门
    # ------------------------------------------------------------------

    def delete_dept(self, dept_id: int) -> dict[str, Any]:
        """
        删除部门（单 ID，不支持批量）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。
        注意: 若部门下存在子部门或关联用户，服务端将返回 code=500。

        Args:
            dept_id: 部门 ID（来自 sys_dept.dept_id）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        return self._wrapper.delete(f"/system/dept/{dept_id}")

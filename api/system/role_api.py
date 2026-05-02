"""
SystemRoleAPI：系统角色相关接口（RuoYi 后端）。

接口列表:
    GET    /system/role/list                        获取角色列表（权限: system:role:list）
    POST   /system/role                             新增角色（权限: system:role:add）
    PUT    /system/role                             修改角色（权限: system:role:edit）
    GET    /system/role/{roleId}                    获取角色详情（权限: system:role:query）
    DELETE /system/role/{roleIds}                   删除角色（权限: system:role:remove）
    PUT    /system/role/dataScope                   修改数据权限（权限: system:role:edit）
    PUT    /system/role/changeStatus                角色状态修改（权限: system:role:edit）
    GET    /system/role/optionselect                获取角色选择框（权限: system:role:query）
    GET    /system/role/authUser/allocatedList      已分配用户列表（权限: system:role:list）
    GET    /system/role/authUser/unallocatedList    未分配用户列表（权限: system:role:list）

模板目录: data/templates/system/
    POST body → add_role.yaml
    PUT  body → update_role.yaml
    PUT  dataScope → update_role_data_scope.yaml
    PUT  changeStatus → change_role_status.yaml

依赖: Authorization: Bearer <token>（通过 set_token() 注入）

add_role 响应示例:
    成功: {"code": 200, "msg": "操作成功"}
    失败(roleKey 重复): {"code": 500, "msg": "新增角色'xxx'失败，角色权限已存在"}

list_roles 响应示例:
    {
        "code": 200,
        "msg": "查询成功",
        "total": 3,
        "rows": [{"roleId": 1, "roleName": "超级管理员", "roleKey": "admin", ...}]
    }
"""
from __future__ import annotations

from typing import Any

from api.system.base_system_api import SystemBaseAPI


class SystemRoleAPI(SystemBaseAPI):
    """系统角色接口，需先注入 Token 才能请求。"""

    _MODULE = "system"

    # ------------------------------------------------------------------
    # 3.1 获取角色列表
    # ------------------------------------------------------------------

    def list_roles(
        self,
        role_name: str | None = None,
        status: str | None = None,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """
        获取角色列表（支持模糊查询和分页）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_name: 角色名称（模糊查询，不传则返回全量）。
            status:    角色状态，"0" 正常 / "1" 停用。
            page_num:  页码（默认 1）。
            page_size: 每页大小（默认 10）。

        Returns:
            响应 body，包含 ``total`` 与 ``rows`` 字段。
        """
        params: dict[str, Any] = {}
        if role_name is not None:
            params["roleName"] = role_name
        if status is not None:
            params["status"] = status
        if page_num is not None:
            params["pageNum"] = page_num
        if page_size is not None:
            params["pageSize"] = page_size
        return self._wrapper.get(
            "/system/role/list", params=params or None,
            _module="system", _api_name="list_roles", _business_type="system:role:list", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.2 新增角色
    # ------------------------------------------------------------------

    def add_role(
        self,
        role_name: str | None = None,
        role_key: str | None = None,
        role_sort: int | None = None,
        status: str | None = None,
        data_scope: str | None = None,
        menu_check_strictly: bool | None = None,
        dept_check_strictly: bool | None = None,
        menu_ids: list[int] | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """
        新增角色。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_name:            角色名称（必填；不传则由模板随机生成）。
            role_key:             角色权限字符串（必填；不传则由模板随机生成）。
            role_sort:            显示顺序（必填；不传则使用模板默认值）。
            status:               角色状态，"0" 正常 / "1" 停用，默认 "0"。
            data_scope:           数据范围（1~5，默认 "1" 全部）。
            menu_check_strictly:  菜单树是否关联显示（默认 True）。
            dept_check_strictly:  部门树是否关联显示（默认 True）。
            menu_ids:             菜单 ID 数组（来自 sys_menu.menu_id）。
            remark:               备注。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {}
        if role_name is not None:
            overrides["payload.roleName"] = role_name
        if role_key is not None:
            overrides["payload.roleKey"] = role_key
        if role_sort is not None:
            overrides["payload.roleSort"] = role_sort
        if status is not None:
            overrides["payload.status"] = status
        if data_scope is not None:
            overrides["payload.dataScope"] = data_scope
        if menu_check_strictly is not None:
            overrides["payload.menuCheckStrictly"] = menu_check_strictly
        if dept_check_strictly is not None:
            overrides["payload.deptCheckStrictly"] = dept_check_strictly
        if menu_ids is not None:
            overrides["payload.menuIds"] = menu_ids
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "add_role", overrides or None)
        return self._wrapper.post(
            "/system/role", json=payload,
            _module="system", _api_name="add_role", _business_type="system:role:add", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.3 修改角色
    # ------------------------------------------------------------------

    def update_role(
        self,
        role_id: int,
        role_name: str,
        role_key: str,
        role_sort: int,
        status: str,
        data_scope: str | None = None,
        menu_check_strictly: bool | None = None,
        dept_check_strictly: bool | None = None,
        menu_ids: list[int] | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """
        修改角色。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。
        注意: roleId/roleName/roleKey/roleSort/status 均为必填，须从 DB 或详情接口取得原值。

        Args:
            role_id:              必填，角色 ID（来自 sys_role.role_id）。
            role_name:            必填，角色名称。
            role_key:             必填，角色权限字符串。
            role_sort:            必填，显示顺序。
            status:               必填，角色状态，"0" 正常 / "1" 停用。
            data_scope:           数据范围（默认 "1"）。
            menu_check_strictly:  菜单树是否关联显示。
            dept_check_strictly:  部门树是否关联显示。
            menu_ids:             菜单 ID 数组。
            remark:               备注。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {
            "payload.roleId": role_id,
            "payload.roleName": role_name,
            "payload.roleKey": role_key,
            "payload.roleSort": role_sort,
            "payload.status": status,
        }
        if data_scope is not None:
            overrides["payload.dataScope"] = data_scope
        if menu_check_strictly is not None:
            overrides["payload.menuCheckStrictly"] = menu_check_strictly
        if dept_check_strictly is not None:
            overrides["payload.deptCheckStrictly"] = dept_check_strictly
        if menu_ids is not None:
            overrides["payload.menuIds"] = menu_ids
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "update_role", overrides)
        return self._wrapper.put(
            "/system/role", json=payload,
            _module="system", _api_name="update_role", _business_type="system:role:edit", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.4 获取角色详情
    # ------------------------------------------------------------------

    def get_role(self, role_id: int) -> dict[str, Any]:
        """
        获取角色详情。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_id: 角色 ID（来自 sys_role.role_id）。

        Returns:
            响应 body，包含角色完整信息。
        """
        return self._wrapper.get(
            f"/system/role/{role_id}",
            _module="system", _api_name="get_role", _business_type="system:role:query", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.5 删除角色
    # ------------------------------------------------------------------

    def delete_roles(self, role_ids: list[int]) -> dict[str, Any]:
        """
        删除角色（支持批量，逗号分隔）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_ids: 角色 ID 列表（对应 sys_role.role_id，避免误删内置超级管理员角色）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        ids_str = ",".join(str(rid) for rid in role_ids)
        return self._wrapper.delete(
            f"/system/role/{ids_str}",
            _module="system", _api_name="delete_roles", _business_type="system:role:remove", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.6 修改数据权限
    # ------------------------------------------------------------------

    def update_data_scope(
        self,
        role_id: int,
        data_scope: str,
        dept_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        修改角色数据权限。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_id:    必填，角色 ID。
            data_scope: 必填，数据范围（"1" 全部 / "2" 自定义 / "3" 本部门 /
                        "4" 本部门及以下 / "5" 仅本人）。
            dept_ids:   部门 ID 数组（dataScope="2" 自定义时需传）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {
            "payload.roleId": role_id,
            "payload.dataScope": data_scope,
        }
        if dept_ids is not None:
            overrides["payload.deptIds"] = dept_ids

        payload = self._build_payload(self._MODULE, "update_role_data_scope", overrides)
        return self._wrapper.put(
            "/system/role/dataScope", json=payload,
            _module="system", _api_name="update_data_scope", _business_type="system:role:edit", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.7 角色状态修改
    # ------------------------------------------------------------------

    def change_status(self, role_id: int, status: str) -> dict[str, Any]:
        """
        修改角色状态（启用/停用）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_id: 角色 ID。
            status:  目标状态，"0" 正常 / "1" 停用。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {
            "payload.roleId": role_id,
            "payload.status": status,
        }
        payload = self._build_payload(self._MODULE, "change_role_status", overrides)
        return self._wrapper.put(
            "/system/role/changeStatus", json=payload,
            _module="system", _api_name="change_status", _business_type="system:role:edit", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.8 获取角色选择框
    # ------------------------------------------------------------------

    def option_select(self) -> dict[str, Any]:
        """
        获取角色选择框列表（通常用于下拉框）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Returns:
            响应 body，包含可选角色列表。
        """
        return self._wrapper.get(
            "/system/role/optionselect",
            _module="system", _api_name="option_select", _business_type="system:role:query", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.9 已分配用户列表
    # ------------------------------------------------------------------

    def allocated_user_list(
        self,
        role_id: int | None = None,
        user_name: str | None = None,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """
        获取已分配该角色的用户列表。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_id:   角色 ID（筛选条件）。
            user_name: 用户名（模糊查询）。
            page_num:  页码。
            page_size: 每页大小。

        Returns:
            响应 body，包含 ``total`` 与 ``rows`` 字段。
        """
        params: dict[str, Any] = {}
        if role_id is not None:
            params["roleId"] = role_id
        if user_name is not None:
            params["userName"] = user_name
        if page_num is not None:
            params["pageNum"] = page_num
        if page_size is not None:
            params["pageSize"] = page_size
        return self._wrapper.get(
            "/system/role/authUser/allocatedList", params=params or None,
            _module="system", _api_name="allocated_user_list", _business_type="system:role:list", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 3.10 未分配用户列表
    # ------------------------------------------------------------------

    def unallocated_user_list(
        self,
        role_id: int | None = None,
        user_name: str | None = None,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """
        获取未分配该角色的用户列表。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            role_id:   角色 ID（筛选条件）。
            user_name: 用户名（模糊查询）。
            page_num:  页码。
            page_size: 每页大小。

        Returns:
            响应 body，包含 ``total`` 与 ``rows`` 字段。
        """
        params: dict[str, Any] = {}
        if role_id is not None:
            params["roleId"] = role_id
        if user_name is not None:
            params["userName"] = user_name
        if page_num is not None:
            params["pageNum"] = page_num
        if page_size is not None:
            params["pageSize"] = page_size
        return self._wrapper.get(
            "/system/role/authUser/unallocatedList", params=params or None,
            _module="system", _api_name="unallocated_user_list", _business_type="system:role:list", _service="ruoyi",
        )

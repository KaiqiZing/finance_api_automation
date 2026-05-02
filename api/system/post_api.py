"""
SystemPostAPI：系统岗位相关接口（RuoYi 后端）。

接口列表:
    GET    /system/post/list           获取岗位列表（权限: system:post:list）
    POST   /system/post                新增岗位（权限: system:post:add）
    PUT    /system/post                修改岗位（权限: system:post:edit）
    GET    /system/post/{postId}       获取岗位详情（权限: system:post:query）
    DELETE /system/post/{postIds}      删除岗位（权限: system:post:remove）
    GET    /system/post/optionselect   获取岗位选择框（权限: system:post:query）

模板目录: data/templates/system/
    POST body → add_post.yaml
    PUT  body → update_post.yaml

依赖: Authorization: Bearer <token>（通过 set_token() 注入）

add_post 响应示例:
    成功: {"code": 200, "msg": "操作成功"}
    失败(postCode 重复): {"code": 500, "msg": "新增岗位'xxx'失败，岗位编码已存在"}

list_posts 响应示例:
    {
        "code": 200,
        "msg": "查询成功",
        "total": 4,
        "rows": [{"postId": 1, "postName": "董事长", "postCode": "ceo", ...}]
    }
"""
from __future__ import annotations

from typing import Any

from api.system.base_system_api import SystemBaseAPI


class SystemPostAPI(SystemBaseAPI):
    """系统岗位接口，需先注入 Token 才能请求。"""

    _MODULE = "system"

    # ------------------------------------------------------------------
    # 6.1 获取岗位列表
    # ------------------------------------------------------------------

    def list_posts(
        self,
        post_code: str | None = None,
        post_name: str | None = None,
        status: str | None = None,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """
        获取岗位列表（支持模糊查询和分页）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            post_code: 岗位编码（模糊查询，不传则返回全量）。
            post_name: 岗位名称（模糊查询）。
            status:    岗位状态，"0" 正常 / "1" 停用。
            page_num:  页码（默认 1）。
            page_size: 每页大小（默认 10）。

        Returns:
            响应 body，包含 ``total`` 与 ``rows`` 字段。
        """
        params: dict[str, Any] = {}
        if post_code is not None:
            params["postCode"] = post_code
        if post_name is not None:
            params["postName"] = post_name
        if status is not None:
            params["status"] = status
        if page_num is not None:
            params["pageNum"] = page_num
        if page_size is not None:
            params["pageSize"] = page_size
        return self._wrapper.get(
            "/system/post/list", params=params or None,
            _module="system", _api_name="list_posts", _business_type="system:post:list", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 6.2 新增岗位
    # ------------------------------------------------------------------

    def add_post(
        self,
        post_code: str | None = None,
        post_name: str | None = None,
        post_sort: int | None = None,
        status: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """
        新增岗位。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            post_code: 岗位编码（必填；不传则由模板随机生成）。
            post_name: 岗位名称（必填；不传则由模板随机生成）。
            post_sort: 显示顺序（必填；不传则由模板默认值）。
            status:    岗位状态，"0" 正常 / "1" 停用（必填；不传则默认 "0"）。
            remark:    备注（可选）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {}
        if post_code is not None:
            overrides["payload.postCode"] = post_code
        if post_name is not None:
            overrides["payload.postName"] = post_name
        if post_sort is not None:
            overrides["payload.postSort"] = post_sort
        if status is not None:
            overrides["payload.status"] = status
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "add_post", overrides or None)
        return self._wrapper.post(
            "/system/post", json=payload,
            _module="system", _api_name="add_post", _business_type="system:post:add", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 6.3 修改岗位
    # ------------------------------------------------------------------

    def update_post(
        self,
        post_id: int,
        post_code: str | None = None,
        post_name: str | None = None,
        post_sort: int | None = None,
        status: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """
        修改岗位。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            post_id:   岗位 ID（必填）。
            post_code: 岗位编码（必填；不传则由模板默认值）。
            post_name: 岗位名称（必填；不传则由模板默认值）。
            post_sort: 显示顺序（必填；不传则由模板默认值）。
            status:    岗位状态，"0" 正常 / "1" 停用。
            remark:    备注（可选）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        overrides: dict[str, Any] = {"payload.postId": post_id}
        if post_code is not None:
            overrides["payload.postCode"] = post_code
        if post_name is not None:
            overrides["payload.postName"] = post_name
        if post_sort is not None:
            overrides["payload.postSort"] = post_sort
        if status is not None:
            overrides["payload.status"] = status
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "update_post", overrides)
        return self._wrapper.put(
            "/system/post", json=payload,
            _module="system", _api_name="update_post", _business_type="system:post:edit", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 6.4 获取岗位详情
    # ------------------------------------------------------------------

    def get_post(self, post_id: int) -> dict[str, Any]:
        """
        获取岗位详情。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            post_id: 岗位 ID（来自 sys_post.post_id）。

        Returns:
            响应 body，包含岗位完整信息。
        """
        return self._wrapper.get(
            f"/system/post/{post_id}",
            _module="system", _api_name="get_post", _business_type="system:post:query", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 6.5 删除岗位
    # ------------------------------------------------------------------

    def delete_posts(self, post_ids: list[int]) -> dict[str, Any]:
        """
        删除岗位（支持批量，逗号分隔）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Args:
            post_ids: 岗位 ID 列表（对应 sys_post.post_id）。

        Returns:
            响应 body，成功时 ``code=200``，失败时 ``code=500`` 且 ``msg`` 含原因。
        """
        ids_str = ",".join(str(pid) for pid in post_ids)
        return self._wrapper.delete(
            f"/system/post/{ids_str}",
            _module="system", _api_name="delete_posts", _business_type="system:post:remove", _service="ruoyi",
        )

    # ------------------------------------------------------------------
    # 6.6 获取岗位选择框
    # ------------------------------------------------------------------

    def option_select(self) -> dict[str, Any]:
        """
        获取岗位选择框列表（通常用于下拉框）。

        前置条件: 已通过 ``set_token(token)`` 注入 Bearer Token。

        Returns:
            响应 body，包含可选岗位列表（``data`` 字段）。
        """
        return self._wrapper.get(
            "/system/post/optionselect",
            _module="system", _api_name="option_select", _business_type="system:post:query", _service="ruoyi",
        )

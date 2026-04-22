"""
SystemNoticeAPI：系统通知公告相关接口（RuoYi 后端）。

接口列表:
    GET    /system/notice/list           获取公告列表（权限: system:notice:list）
    POST   /system/notice                新增公告（权限: system:notice:add）
    PUT    /system/notice                修改公告（权限: system:notice:edit）
    GET    /system/notice/{noticeId}     获取公告详情（权限: system:notice:query）
    DELETE /system/notice/{noticeIds}    删除公告（权限: system:notice:remove）

模板目录: data/templates/system/
    POST body → add_notice.yaml
    PUT  body → update_notice.yaml

依赖: Authorization: Bearer <token>（通过 set_token() 注入）

枚举:
    noticeType  1 通知 / 2 公告
    status      0 正常 / 1 关闭
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI
from config.settings import cfg
from core.request_wrapper import RequestConfig, RequestWrapper


class SystemNoticeAPI(BaseAPI):
    """系统通知公告接口，需先注入 Token 才能请求。"""

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

    def list_notices(
        self,
        notice_title: str | None = None,
        notice_type: str | None = None,
        status: str | None = None,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """获取公告列表（支持筛选与分页）。"""
        params: dict[str, Any] = {}
        if notice_title is not None:
            params["noticeTitle"] = notice_title
        if notice_type is not None:
            params["noticeType"] = notice_type
        if status is not None:
            params["status"] = status
        if page_num is not None:
            params["pageNum"] = page_num
        if page_size is not None:
            params["pageSize"] = page_size
        return self._wrapper.get("/system/notice/list", params=params or None)

    def add_notice(
        self,
        notice_title: str | None = None,
        notice_type: str | None = None,
        notice_content: str | None = None,
        status: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """新增公告。noticeTitle、noticeType 必填；不传则由模板生成。"""
        overrides: dict[str, Any] = {}
        if notice_title is not None:
            overrides["payload.noticeTitle"] = notice_title
        if notice_type is not None:
            overrides["payload.noticeType"] = notice_type
        if notice_content is not None:
            overrides["payload.noticeContent"] = notice_content
        if status is not None:
            overrides["payload.status"] = status
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "add_notice", overrides or None)
        return self._wrapper.post("/system/notice", json=payload)

    def update_notice(
        self,
        notice_id: int,
        notice_title: str | None = None,
        notice_type: str | None = None,
        notice_content: str | None = None,
        status: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        """修改公告。noticeId 必填。"""
        overrides: dict[str, Any] = {"payload.noticeId": notice_id}
        if notice_title is not None:
            overrides["payload.noticeTitle"] = notice_title
        if notice_type is not None:
            overrides["payload.noticeType"] = notice_type
        if notice_content is not None:
            overrides["payload.noticeContent"] = notice_content
        if status is not None:
            overrides["payload.status"] = status
        if remark is not None:
            overrides["payload.remark"] = remark

        payload = self._build_payload(self._MODULE, "update_notice", overrides)
        return self._wrapper.put("/system/notice", json=payload)

    def get_notice(self, notice_id: int) -> dict[str, Any]:
        """获取公告详情。"""
        return self._wrapper.get(f"/system/notice/{notice_id}")

    def delete_notices(self, notice_ids: list[int]) -> dict[str, Any]:
        """删除公告（支持批量，路径参数逗号分隔）。"""
        ids_str = ",".join(str(nid) for nid in notice_ids)
        return self._wrapper.delete(f"/system/notice/{ids_str}")

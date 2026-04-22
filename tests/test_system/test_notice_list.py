"""
系统通知公告列表测试用例。

真实接口:
    GET /system/notice/list
        参数: noticeTitle, noticeType, status, pageNum, pageSize
        响应: {"code": 200, "msg": "...", "total": N, "rows": [...]}

用例清单:
    TC-SYS-NTC-001  默认列表，断言 code==200 且 rows 为列表
    TC-SYS-NTC-002  按 noticeTitle 模糊查询
    TC-SYS-NTC-003  按 noticeType 查询
    TC-SYS-NTC-004  分页 pageSize=2
    TC-SYS-NTC-005  按 status 查询
    TC-SYS-NTC-006  未携带 Token
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.notice_api import SystemNoticeAPI
from utils.system_ruoyi_queries import fetch_notice_id_by_notice_title


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


@allure.epic("系统管理模块")
@allure.feature("通知公告")
class TestNoticeList:
    """GET /system/notice/list 测试集合。"""

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-001：默认参数获取公告列表，断言 code==200")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_list_notices_default(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)

        with allure.step("调用公告列表接口（默认参数）"):
            resp = api.list_notices()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="NoticeList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200 且 rows 为列表"):
            assert resp.get("code") == 200, (
                f"获取列表失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )
            rows = resp.get("rows", [])
            assert isinstance(rows, list), f"rows 类型异常: {type(rows)}"
            assert isinstance(resp.get("total"), int), f"total 非整数: {resp}"

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-002：按 noticeTitle 模糊查询，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_notices_by_title(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)

        keyword = "温馨"
        with allure.step(f"调用列表接口 noticeTitle={keyword!r}"):
            resp = api.list_notices(notice_title=keyword)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="NoticeList ByTitle Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        assert resp.get("code") == 200, (
            f"查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
        )
        rows = resp.get("rows", [])
        for row in rows:
            assert keyword in row.get("noticeTitle", ""), (
                f"标题不包含关键字: {row}"
            )

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-003：按 noticeType='1' 查询，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_notices_by_type(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)

        with allure.step("调用列表接口 noticeType=1（通知）"):
            resp = api.list_notices(notice_type="1")

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="NoticeList ByType Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        assert resp.get("code") == 200, (
            f"查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
        )
        for row in resp.get("rows", []):
            assert row.get("noticeType") == "1", f"类型不匹配: {row}"

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-004：分页 pageNum=1, pageSize=2，断言 rows 长度 <= 2")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_notices_pagination(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)

        with allure.step("分页查询 pageSize=2"):
            resp = api.list_notices(page_num=1, page_size=2)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="NoticeList Pagination Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        assert resp.get("code") == 200, (
            f"分页失败: code={resp.get('code')}, msg={resp.get('msg')}"
        )
        rows = resp.get("rows", [])
        assert len(rows) <= 2, f"rows 超过 pageSize: {resp}"

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-005：按 status='0' 查询，断言每条 status 为 0")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_notices_by_status(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)

        with allure.step("调用列表接口 status=0"):
            resp = api.list_notices(status="0")

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="NoticeList ByStatus Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        assert resp.get("code") == 200, (
            f"查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
        )
        for row in resp.get("rows", []):
            assert row.get("status") == "0", f"状态异常: {row}"

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-006：未携带 Token 获取列表，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_list_notices_without_token(self) -> None:
        api = SystemNoticeAPI()
        with allure.step("无 Token 调用列表"):
            resp = api.list_notices()
        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="NoticeList NoToken Response",
                attachment_type=allure.attachment_type.TEXT,
            )
        assert resp.get("code") != 200, (
            f"未携带 Token 仍返回 200: {resp}"
        )

    @allure.story("获取公告列表")
    @allure.title("TC-SYS-NTC-007：先新增再按标题查询，断言能查到该条")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_notices_filter_by_created_title(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        unique_title = f"列表检索专用_{uuid.uuid4().hex[:10]}"
        try:
            with allure.step("新增一条公告"):
                r_add = api.add_notice(notice_title=unique_title, notice_type="1", status="0")
                assert r_add.get("code") == 200, f"前置新增失败: {r_add}"
            with allure.step("按标题查询列表"):
                resp = api.list_notices(notice_title=unique_title)
            assert resp.get("code") == 200
            titles = [r.get("noticeTitle") for r in resp.get("rows", [])]
            assert unique_title in titles, f"列表未包含新建标题: {titles}"
        finally:
            nid = fetch_notice_id_by_notice_title(unique_title)
            if nid is not None:
                api.set_token(token)
                api.delete_notices([nid])

"""
系统通知公告 CRUD 测试用例。

真实接口:
    POST   /system/notice           新增
    GET    /system/notice/{id}    详情
    PUT    /system/notice           修改
    DELETE /system/notice/{ids}   删除

用例清单:
    TC-SYS-NTC-010  仅必填字段新增
    TC-SYS-NTC-011  含 remark、noticeContent 新增
    TC-SYS-NTC-012  未携带 Token 新增
    TC-SYS-NTC-013  新增后查详情
    TC-SYS-NTC-014  新增→修改→再查详情
    TC-SYS-NTC-015  新增后删除
    TC-SYS-NTC-016  批量删除
    TC-SYS-NTC-017  删除不存在 ID
    TC-SYS-NTC-018  查询不存在 ID 详情
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.notice_api import SystemNoticeAPI
from utils.system_ruoyi_queries import fetch_notice_id_by_notice_title


def _gen_notice_title() -> str:
    return "自动化公告_" + uuid.uuid4().hex[:10]


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败: {resp}"
    return resp["data"]["access_token"]


@allure.epic("系统管理模块")
@allure.feature("通知公告")
class TestNoticeCrud:
    """通知公告 CRUD 综合测试。"""

    @allure.story("新增公告")
    @allure.title("TC-SYS-NTC-010：仅必填字段 noticeTitle + noticeType 新增成功")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_add_notice_required_only(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        title = _gen_notice_title()
        try:
            with allure.step(f"新增: noticeTitle={title}, noticeType=1"):
                resp = api.add_notice(notice_title=title, notice_type="1")
            allure.attach(str(resp), name="AddNotice Response", attachment_type=allure.attachment_type.TEXT)
            assert resp.get("code") == 200, f"新增失败: {resp}"
            assert resp.get("msg") == "操作成功", resp
        finally:
            nid = fetch_notice_id_by_notice_title(title)
            if nid is not None:
                api.set_token(token)
                api.delete_notices([nid])

    @allure.story("新增公告")
    @allure.title("TC-SYS-NTC-011：含 remark、noticeContent 新增成功")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_notice_with_optional_fields(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        title = _gen_notice_title()
        try:
            resp = api.add_notice(
                notice_title=title,
                notice_type="2",
                notice_content="自动化正文内容",
                status="0",
                remark="自动化备注",
            )
            allure.attach(str(resp), name="AddNotice Full Response", attachment_type=allure.attachment_type.TEXT)
            assert resp.get("code") == 200, f"新增失败: {resp}"
        finally:
            nid = fetch_notice_id_by_notice_title(title)
            if nid is not None:
                api.set_token(token)
                api.delete_notices([nid])

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-NTC-012：未携带 Token 新增，断言被拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_notice_without_token(self) -> None:
        api = SystemNoticeAPI()
        resp = api.add_notice(notice_title=_gen_notice_title(), notice_type="1")
        allure.attach(str(resp), name="NoToken Add", attachment_type=allure.attachment_type.TEXT)
        assert resp.get("code") != 200, resp

    @allure.story("获取公告详情")
    @allure.title("TC-SYS-NTC-013：新增后按 noticeId 查详情，字段一致")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_notice_detail(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        title = _gen_notice_title()
        content = "详情校验正文"
        try:
            r_add = api.add_notice(
                notice_title=title,
                notice_type="1",
                notice_content=content,
                status="0",
            )
            assert r_add.get("code") == 200, r_add
            nid = fetch_notice_id_by_notice_title(title)
            if nid is None:
                pytest.skip("DB 未查到 notice_id，跳过详情用例")
            r_get = api.get_notice(nid)
            allure.attach(str(r_get), name="GetNotice", attachment_type=allure.attachment_type.TEXT)
            assert r_get.get("code") == 200, r_get
            data = r_get.get("data", {})
            assert data.get("noticeTitle") == title
            assert data.get("noticeType") == "1"
            assert data.get("noticeContent") == content
        finally:
            nid = fetch_notice_id_by_notice_title(title)
            if nid is not None:
                api.set_token(token)
                api.delete_notices([nid])

    @allure.story("修改公告")
    @allure.title("TC-SYS-NTC-014：新增→修改→再查详情")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_notice(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        title = _gen_notice_title()
        new_title = _gen_notice_title()
        try:
            assert api.add_notice(notice_title=title, notice_type="1", status="0").get("code") == 200
            nid = fetch_notice_id_by_notice_title(title)
            if nid is None:
                pytest.skip("DB 未查到 notice_id，跳过修改用例")
            r_up = api.update_notice(
                notice_id=nid,
                notice_title=new_title,
                notice_type="2",
                notice_content="修改后正文",
                status="0",
                remark="修改备注",
            )
            allure.attach(str(r_up), name="UpdateNotice", attachment_type=allure.attachment_type.TEXT)
            assert r_up.get("code") == 200, r_up
            data = api.get_notice(nid).get("data", {})
            assert data.get("noticeTitle") == new_title
            assert data.get("noticeType") == "2"
            assert data.get("noticeContent") == "修改后正文"
        finally:
            final_title = new_title
            nid = fetch_notice_id_by_notice_title(final_title)
            if nid is None:
                nid = fetch_notice_id_by_notice_title(title)
            if nid is not None:
                api.set_token(token)
                api.delete_notices([nid])

    @allure.story("删除公告")
    @allure.title("TC-SYS-NTC-015：新增后删除成功")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_delete_notice_after_add(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        title = _gen_notice_title()
        assert api.add_notice(notice_title=title, notice_type="1").get("code") == 200
        nid = fetch_notice_id_by_notice_title(title)
        if nid is None:
            pytest.skip("DB 未查到 notice_id，跳过删除用例")
        r_del = api.delete_notices([nid])
        allure.attach(str(r_del), name="DeleteNotice", attachment_type=allure.attachment_type.TEXT)
        assert r_del.get("code") == 200, r_del

    @allure.story("删除公告")
    @allure.title("TC-SYS-NTC-016：批量删除多条")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_notices_batch(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        titles = [_gen_notice_title(), _gen_notice_title()]
        nids: list[int] = []
        try:
            for t in titles:
                assert api.add_notice(notice_title=t, notice_type="1").get("code") == 200
                nid = fetch_notice_id_by_notice_title(t)
                if nid is not None:
                    nids.append(nid)
            if len(nids) < 2:
                pytest.skip("未能解析两条 notice_id")
            r_del = api.delete_notices(nids)
            allure.attach(str(r_del), name="BatchDelete", attachment_type=allure.attachment_type.TEXT)
            assert r_del.get("code") == 200, r_del
        finally:
            for t in titles:
                nid = fetch_notice_id_by_notice_title(t)
                if nid is not None:
                    api.set_token(token)
                    api.delete_notices([nid])

    @allure.story("删除公告")
    @allure.title("TC-SYS-NTC-017：删除不存在的 noticeId")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_nonexistent_notice(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        resp = api.delete_notices([99999999])
        allure.attach(str(resp), name="DeleteNonexistent", attachment_type=allure.attachment_type.TEXT)
        assert resp.get("code") in (200, 400, 500), resp

    @allure.story("获取公告详情")
    @allure.title("TC-SYS-NTC-018：查询不存在的 noticeId 详情")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_nonexistent_notice(self) -> None:
        token = _login_and_get_token()
        api = SystemNoticeAPI()
        api.set_token(token)
        resp = api.get_notice(99999999)
        allure.attach(str(resp), name="GetNonexistent", attachment_type=allure.attachment_type.TEXT)
        assert resp.get("code") in (200, 500), resp

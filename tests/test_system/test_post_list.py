"""
系统岗位列表 测试用例。

真实接口:
    GET http://192.168.0.107/dev-api/system/post/list
        请求头: Authorization: Bearer <access_token>
        请求参数: postCode(模糊), postName(模糊), status, pageNum, pageSize
        响应体: {"code": 200, "msg": "查询成功", "total": N, "rows": [...]}

    GET http://192.168.0.107/dev-api/system/post/optionselect
        请求头: Authorization: Bearer <access_token>
        响应体: {"code": 200, "data": [...]}

用例清单:
    TC-SYS-PST-001  不带任何参数获取岗位列表，断言 code==200 且 rows 非空
    TC-SYS-PST-002  按 postName 模糊查询"董事长"，断言 code==200
    TC-SYS-PST-003  按 postCode 模糊查询"ceo"，断言 code==200
    TC-SYS-PST-004  分页查询（pageNum=1, pageSize=2），断言 rows 长度 <= 2
    TC-SYS-PST-005  按 status="0" 查询正常状态岗位，断言返回的每条 rows 状态均为正常
    TC-SYS-PST-006  未携带 Token 获取列表，断言被鉴权拦截
    TC-SYS-PST-007  获取岗位选择框列表，断言 code==200 且 data 为列表
"""
from __future__ import annotations

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.post_api import SystemPostAPI


# ==============================================================================
# 辅助函数
# ==============================================================================

def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("岗位管理")
class TestPostList:
    """岗位列表接口 GET /system/post/list 测试集合。"""

    # ==================================================================
    # TC-SYS-PST-001：默认参数获取岗位列表
    # ==================================================================

    @allure.story("获取岗位列表")
    @allure.title("TC-SYS-PST-001：不带参数获取岗位列表，断言 code==200 且 rows 非空")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_list_posts_default(self) -> None:
        """
        不带任何过滤参数，断言:
        - 响应 code == 200
        - rows 列表非空（系统初始化至少包含若干岗位）
        - total >= 1
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        with allure.step("调用岗位列表接口（默认参数）: GET /system/post/list"):
            resp = post_api.list_posts()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"获取岗位列表失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 rows 非空且 total >= 1"):
            rows = resp.get("rows", [])
            total = resp.get("total", 0)
            assert len(rows) > 0, f"posts rows 为空，完整响应: {resp}"
            assert total >= 1, f"total 异常: {total}"

    # ==================================================================
    # TC-SYS-PST-002：按 postName 模糊查询
    # ==================================================================

    @allure.story("获取岗位列表")
    @allure.title("TC-SYS-PST-002：按 postName='董事长' 模糊查询，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_posts_by_name(self) -> None:
        """
        传入 postName 模糊查询，断言:
        - 响应 code == 200
        - 若有匹配项则 rows 中每条 postName 包含查询关键字
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        keyword = "董事长"
        with allure.step(f"调用岗位列表接口（postName={keyword}）"):
            resp = post_api.list_posts(post_name=keyword)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostList ByName Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"按 postName 查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("若有返回，断言每条 postName 包含关键字"):
            rows = resp.get("rows", [])
            for row in rows:
                assert keyword in row.get("postName", ""), (
                    f"返回岗位名称不包含关键字 '{keyword}': {row}"
                )

    # ==================================================================
    # TC-SYS-PST-003：按 postCode 模糊查询
    # ==================================================================

    @allure.story("获取岗位列表")
    @allure.title("TC-SYS-PST-003：按 postCode='ceo' 模糊查询，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_posts_by_code(self) -> None:
        """
        传入 postCode 模糊查询，断言:
        - 响应 code == 200
        - 若有匹配项则 rows 中每条 postCode 包含查询关键字
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        keyword = "ceo"
        with allure.step(f"调用岗位列表接口（postCode={keyword}）"):
            resp = post_api.list_posts(post_code=keyword)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostList ByCode Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"按 postCode 查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("若有返回，断言每条 postCode 包含关键字"):
            rows = resp.get("rows", [])
            for row in rows:
                assert keyword.lower() in row.get("postCode", "").lower(), (
                    f"返回岗位编码不包含关键字 '{keyword}': {row}"
                )

    # ==================================================================
    # TC-SYS-PST-004：分页查询
    # ==================================================================

    @allure.story("获取岗位列表")
    @allure.title("TC-SYS-PST-004：分页查询（pageNum=1, pageSize=2），断言 rows 长度 <= 2")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_posts_pagination(self) -> None:
        """
        传入分页参数，断言:
        - 响应 code == 200
        - rows 长度 <= pageSize
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        with allure.step("调用岗位列表接口（pageNum=1, pageSize=2）"):
            resp = post_api.list_posts(page_num=1, page_size=2)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostList Pagination Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"分页查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 rows 长度 <= 2"):
            rows = resp.get("rows", [])
            assert len(rows) <= 2, f"rows 长度 {len(rows)} 超过 pageSize=2，完整响应: {resp}"

    # ==================================================================
    # TC-SYS-PST-005：按 status 过滤
    # ==================================================================

    @allure.story("获取岗位列表")
    @allure.title("TC-SYS-PST-005：按 status='0' 查询正常状态岗位，断言每条 status 均为正常")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_posts_by_status(self) -> None:
        """
        传入 status="0"，断言:
        - 响应 code == 200
        - rows 中每条记录的 status 字段为 "0"
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        with allure.step("调用岗位列表接口（status='0'）"):
            resp = post_api.list_posts(status="0")

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostList ByStatus Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"按 status 查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 rows 中每条 status == '0'"):
            rows = resp.get("rows", [])
            for row in rows:
                assert row.get("status") == "0", (
                    f"存在非正常状态岗位: {row}"
                )

    # ==================================================================
    # TC-SYS-PST-006：未携带 Token 获取列表
    # ==================================================================

    @allure.story("获取岗位列表")
    @allure.title("TC-SYS-PST-006：未携带 Token 获取岗位列表，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_list_posts_without_token(self) -> None:
        """
        不注入 Token，断言:
        - 响应 code != 200（若依鉴权一般返回 401）
        """
        post_api = SystemPostAPI()

        with allure.step("调用岗位列表接口（无 Token）"):
            resp = post_api.list_posts()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostList NoToken Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code != 200，表明被鉴权拦截"):
            assert resp.get("code") != 200, (
                f"未携带 Token 仍返回 200，存在鉴权漏洞，完整响应: {resp}"
            )

    # ==================================================================
    # TC-SYS-PST-007：获取岗位选择框
    # ==================================================================

    @allure.story("获取岗位选择框")
    @allure.title("TC-SYS-PST-007：获取岗位选择框列表，断言 code==200 且 data 为列表")
    @allure.severity(allure.severity_level.NORMAL)
    def test_option_select(self) -> None:
        """
        调用 optionselect 接口，断言:
        - 响应 code == 200
        - data 字段为列表类型
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        with allure.step("调用岗位选择框接口: GET /system/post/optionselect"):
            resp = post_api.option_select()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="PostOptionSelect Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"获取岗位选择框失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 data 为列表"):
            data = resp.get("data")
            assert isinstance(data, list), f"data 不是列表类型: {type(data)}, 完整响应: {resp}"

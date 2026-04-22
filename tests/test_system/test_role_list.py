"""
系统角色列表 测试用例。

真实接口:
    GET http://192.168.0.107/dev-api/system/role/list
        请求头: Authorization: Bearer <access_token>
        请求参数: roleName(模糊), status, pageNum, pageSize
        响应体: {"code": 200, "msg": "查询成功", "total": N, "rows": [...]}

    GET http://192.168.0.107/dev-api/system/role/optionselect
        请求头: Authorization: Bearer <access_token>
        响应体: {"code": 200, "data": [...]}

用例清单:
    TC-SYS-ROL-001  不带任何参数获取角色列表，断言 code==200 且 rows 非空
    TC-SYS-ROL-002  按 roleName 模糊查询"管理员"，断言 code==200
    TC-SYS-ROL-003  分页查询（pageNum=1, pageSize=5），断言 rows 长度 <= 5
    TC-SYS-ROL-004  按 status="0" 查询正常状态角色，断言返回的每条 rows 状态均为正常
    TC-SYS-ROL-005  未携带 Token 获取列表，断言被鉴权拦截
    TC-SYS-ROL-006  获取角色选择框列表，断言 code==200 且 data 为列表
"""
from __future__ import annotations

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.role_api import SystemRoleAPI


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
@allure.feature("角色管理")
class TestRoleList:
    """角色列表接口 GET /system/role/list 测试集合。"""

    # ==================================================================
    # TC-SYS-ROL-001：默认参数获取角色列表
    # ==================================================================

    @allure.story("获取角色列表")
    @allure.title("TC-SYS-ROL-001：不带参数获取角色列表，断言 code==200 且 rows 非空")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_list_roles_default(self) -> None:
        """
        不带任何过滤参数，断言:
        - 响应 code == 200
        - rows 列表非空（系统初始化至少包含超级管理员角色）
        - total >= 1
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("调用角色列表接口（默认参数）: GET /system/role/list"):
            resp = role_api.list_roles()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="RoleList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"获取角色列表失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 rows 非空且 total >= 1"):
            rows = resp.get("rows", [])
            total = resp.get("total", 0)
            assert len(rows) > 0, f"roles rows 为空，完整响应: {resp}"
            assert total >= 1, f"total 异常: {total}"

    # ==================================================================
    # TC-SYS-ROL-002：按 roleName 模糊查询
    # ==================================================================

    @allure.story("获取角色列表")
    @allure.title("TC-SYS-ROL-002：按 roleName='管理员' 模糊查询，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_roles_by_name(self) -> None:
        """
        传入 roleName 模糊查询，断言:
        - 响应 code == 200
        - 返回的每条 row 中 roleName 均包含查询关键字
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        keyword = "管理员"

        with allure.step(f"调用角色列表接口（roleName='{keyword}'）"):
            resp = role_api.list_roles(role_name=keyword)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="RoleList ByName Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"模糊查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言返回的 row 中 roleName 均含关键字"):
            rows = resp.get("rows", [])
            for row in rows:
                assert keyword in row.get("roleName", ""), (
                    f"roleName={row.get('roleName')!r} 不含关键字 '{keyword}'"
                )

    # ==================================================================
    # TC-SYS-ROL-003：分页查询
    # ==================================================================

    @allure.story("获取角色列表")
    @allure.title("TC-SYS-ROL-003：分页查询（pageNum=1, pageSize=5），断言 rows 长度 <= 5")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_roles_pagination(self) -> None:
        """
        指定分页参数，断言:
        - 响应 code == 200
        - rows 长度不超过 pageSize
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("调用角色列表接口（pageNum=1, pageSize=5）"):
            resp = role_api.list_roles(page_num=1, page_size=5)

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"分页查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 rows 长度 <= 5"):
            rows = resp.get("rows", [])
            assert len(rows) <= 5, f"分页 rows 长度={len(rows)} 超过 pageSize=5"

    # ==================================================================
    # TC-SYS-ROL-004：按状态筛选
    # ==================================================================

    @allure.story("获取角色列表")
    @allure.title("TC-SYS-ROL-004：按 status='0' 查询正常状态角色，断言每条记录 status 均为正常")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_roles_by_status(self) -> None:
        """
        传入 status='0' 过滤，断言:
        - 响应 code == 200
        - 返回的每条 row 中 status 均为 "0"
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("调用角色列表接口（status='0'）"):
            resp = role_api.list_roles(status="0")

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"按状态查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言每条 row 的 status 均为 '0'"):
            rows = resp.get("rows", [])
            for row in rows:
                assert row.get("status") == "0", (
                    f"期望 status='0'，实际 status={row.get('status')!r}，roleId={row.get('roleId')}"
                )

    # ==================================================================
    # TC-SYS-ROL-005：未携带 Token 鉴权拦截
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-ROL-005：未携带 Token 获取角色列表，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_list_roles_without_token(self) -> None:
        """
        不注入 Token 直接请求，断言:
        - 响应 code != 200（通常为 401）
        """
        role_api = SystemRoleAPI()

        with allure.step("不注入 Token，调用角色列表接口"):
            resp = role_api.list_roles()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

    # ==================================================================
    # TC-SYS-ROL-006：获取角色选择框
    # ==================================================================

    @allure.story("获取角色选择框")
    @allure.title("TC-SYS-ROL-006：获取角色选择框列表，断言 code==200 且 data 为列表")
    @allure.severity(allure.severity_level.NORMAL)
    def test_option_select(self) -> None:
        """
        调用 optionselect 接口，断言:
        - 响应 code == 200
        - data 字段为列表类型且非空
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("调用角色选择框接口: GET /system/role/optionselect"):
            resp = role_api.option_select()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="OptionSelect Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"获取选择框失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 data 为非空列表"):
            data = resp.get("data", [])
            assert isinstance(data, list), f"data 类型应为 list，实际: {type(data)}"
            assert len(data) > 0, f"data 列表为空，完整响应: {resp}"

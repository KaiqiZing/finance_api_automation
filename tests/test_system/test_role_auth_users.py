"""
系统角色 已分配/未分配用户列表 测试用例。

真实接口:
    GET http://192.168.0.107/dev-api/system/role/authUser/allocatedList
        请求头: Authorization: Bearer <access_token>
        请求参数: roleId, userName, pageNum, pageSize

    GET http://192.168.0.107/dev-api/system/role/authUser/unallocatedList
        请求头: Authorization: Bearer <access_token>
        请求参数: roleId, userName, pageNum, pageSize

用例清单:
    TC-SYS-ROL-030  查询指定角色的已分配用户列表，断言 code==200 且响应结构正确
    TC-SYS-ROL-031  按 userName 过滤已分配用户，断言返回的每条记录含 userName
    TC-SYS-ROL-032  分页查询已分配用户（pageSize=5），断言 rows 长度 <= 5
    TC-SYS-ROL-033  查询指定角色的未分配用户列表，断言 code==200 且响应结构正确
    TC-SYS-ROL-034  按 userName 过滤未分配用户，断言 code==200
    TC-SYS-ROL-035  未携带 Token 查询已分配列表，断言被鉴权拦截
"""
from __future__ import annotations

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.role_api import SystemRoleAPI
from utils.system_ruoyi_queries import fetch_one_role_id


# ==============================================================================
# 辅助函数
# ==============================================================================

def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


# ==============================================================================
# 测试类：已分配用户列表
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("角色管理")
class TestRoleAllocatedUsers:
    """角色已分配用户列表 GET /system/role/authUser/allocatedList 测试集合。"""

    # ==================================================================
    # TC-SYS-ROL-030：查询已分配用户列表
    # ==================================================================

    @allure.story("已分配用户列表")
    @allure.title("TC-SYS-ROL-030：查询指定角色的已分配用户列表，断言 code==200 且响应结构正确")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_allocated_list_by_role(self) -> None:
        """
        从 DB 随机取一个有效角色 ID，查询其已分配用户，断言:
        - 响应 code == 200
        - 响应包含 total 与 rows 字段
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("从 DB 随机获取一个有效角色 ID"):
            role_id = fetch_one_role_id()
            if role_id is None:
                pytest.skip("sys_role 中无可用普通角色，跳过已分配用户测试")

        allure.attach(
            body=f"role_id={role_id}",
            name="查询条件",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用已分配用户接口: roleId={role_id}"):
            resp = role_api.allocated_user_list(role_id=role_id)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AllocatedList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"已分配用户列表失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言响应包含 total 与 rows 字段"):
            assert "total" in resp, f"响应缺少 total 字段: {resp}"
            assert "rows" in resp, f"响应缺少 rows 字段: {resp}"
            assert isinstance(resp["rows"], list), f"rows 类型应为 list: {type(resp['rows'])}"

    # ==================================================================
    # TC-SYS-ROL-031：按 userName 过滤已分配用户
    # ==================================================================

    @allure.story("已分配用户列表")
    @allure.title("TC-SYS-ROL-031：按 userName='admin' 过滤已分配用户，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_allocated_list_filter_by_username(self) -> None:
        """
        传入 userName 过滤条件，断言:
        - 响应 code == 200
        - 若有结果，每条记录的 userName 含查询关键字
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("从 DB 随机获取一个有效角色 ID"):
            role_id = fetch_one_role_id()
            if role_id is None:
                pytest.skip("sys_role 中无可用普通角色，跳过测试")

        with allure.step(f"调用已分配用户接口（roleId={role_id}, userName='admin'）"):
            resp = role_api.allocated_user_list(role_id=role_id, user_name="admin")

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"按 userName 过滤失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("若有结果，断言每条记录 userName 含 'admin'"):
            rows = resp.get("rows", [])
            for row in rows:
                assert "admin" in row.get("userName", ""), (
                    f"userName={row.get('userName')!r} 不含 'admin'"
                )

    # ==================================================================
    # TC-SYS-ROL-032：分页查询已分配用户
    # ==================================================================

    @allure.story("已分配用户列表")
    @allure.title("TC-SYS-ROL-032：分页查询已分配用户（pageSize=5），断言 rows 长度 <= 5")
    @allure.severity(allure.severity_level.NORMAL)
    def test_allocated_list_pagination(self) -> None:
        """分页查询，断言 rows 长度不超过 pageSize。"""
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("从 DB 随机获取一个有效角色 ID"):
            role_id = fetch_one_role_id()
            if role_id is None:
                pytest.skip("sys_role 中无可用普通角色，跳过测试")

        with allure.step(f"调用已分配用户接口（roleId={role_id}, pageNum=1, pageSize=5）"):
            resp = role_api.allocated_user_list(role_id=role_id, page_num=1, page_size=5)

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"分页查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 rows 长度 <= 5"):
            rows = resp.get("rows", [])
            assert len(rows) <= 5, f"rows 长度={len(rows)} 超过 pageSize=5"


# ==============================================================================
# 测试类：未分配用户列表
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("角色管理")
class TestRoleUnallocatedUsers:
    """角色未分配用户列表 GET /system/role/authUser/unallocatedList 测试集合。"""

    # ==================================================================
    # TC-SYS-ROL-033：查询未分配用户列表
    # ==================================================================

    @allure.story("未分配用户列表")
    @allure.title("TC-SYS-ROL-033：查询指定角色的未分配用户列表，断言 code==200 且响应结构正确")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_unallocated_list_by_role(self) -> None:
        """
        从 DB 随机取一个有效角色 ID，查询其未分配用户，断言:
        - 响应 code == 200
        - 响应包含 total 与 rows 字段
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("从 DB 随机获取一个有效角色 ID"):
            role_id = fetch_one_role_id()
            if role_id is None:
                pytest.skip("sys_role 中无可用普通角色，跳过未分配用户测试")

        allure.attach(
            body=f"role_id={role_id}",
            name="查询条件",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用未分配用户接口: roleId={role_id}"):
            resp = role_api.unallocated_user_list(role_id=role_id)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="UnallocatedList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"未分配用户列表失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言响应包含 total 与 rows 字段"):
            assert "total" in resp, f"响应缺少 total 字段: {resp}"
            assert "rows" in resp, f"响应缺少 rows 字段: {resp}"
            assert isinstance(resp["rows"], list), f"rows 类型应为 list: {type(resp['rows'])}"

    # ==================================================================
    # TC-SYS-ROL-034：按 userName 过滤未分配用户
    # ==================================================================

    @allure.story("未分配用户列表")
    @allure.title("TC-SYS-ROL-034：按 userName 过滤未分配用户，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_unallocated_list_filter_by_username(self) -> None:
        """
        传入 userName 过滤，断言:
        - 响应 code == 200
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        with allure.step("从 DB 随机获取一个有效角色 ID"):
            role_id = fetch_one_role_id()
            if role_id is None:
                pytest.skip("sys_role 中无可用普通角色，跳过测试")

        with allure.step(f"调用未分配用户接口（roleId={role_id}, userName='test'）"):
            resp = role_api.unallocated_user_list(role_id=role_id, user_name="test")

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"按 userName 过滤失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-ROL-035：未携带 Token 查询已分配列表
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-ROL-035：未携带 Token 查询已分配用户列表，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_allocated_list_without_token(self) -> None:
        """
        不注入 Token 直接查询，断言:
        - 响应 code != 200（通常为 401）
        """
        role_api = SystemRoleAPI()

        with allure.step("不注入 Token，调用已分配用户列表接口（roleId=2）"):
            resp = role_api.allocated_user_list(role_id=2)

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token AllocatedList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

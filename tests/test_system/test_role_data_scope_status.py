"""
系统角色 数据权限 & 状态变更 测试用例。

真实接口:
    PUT http://192.168.0.107/dev-api/system/role/dataScope
        请求体: {"roleId": N, "dataScope": "1", "deptIds": [...]}

    PUT http://192.168.0.107/dev-api/system/role/changeStatus
        请求体: {"roleId": N, "status": "1"}

用例清单:
    TC-SYS-ROL-020  修改数据权限为"全部数据"，断言 code==200
    TC-SYS-ROL-021  修改数据权限为"本部门"，断言 code==200
    TC-SYS-ROL-022  修改数据权限为"仅本人"，断言 code==200
    TC-SYS-ROL-023  数据驱动：dataScope 枚举 1~5 均可修改成功
    TC-SYS-ROL-024  修改角色状态为停用（status="1"），断言 code==200
    TC-SYS-ROL-025  修改角色状态为正常（status="0"），断言 code==200
    TC-SYS-ROL-026  未携带 Token 修改状态，断言被鉴权拦截
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.role_api import SystemRoleAPI
from utils.system_ruoyi_queries import fetch_role_id_by_role_key


# ==============================================================================
# 辅助函数
# ==============================================================================

def _gen_role_key() -> str:
    return "test_role_" + uuid.uuid4().hex[:8]


def _gen_role_name() -> str:
    return "测试角色_" + uuid.uuid4().hex[:6]


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


def _create_test_role(role_api: SystemRoleAPI) -> tuple[int, str]:
    """新增测试角色，返回 (role_id, role_key)；调用方负责删除。"""
    role_key = _gen_role_key()
    resp = role_api.add_role(
        role_name=_gen_role_name(),
        role_key=role_key,
        role_sort=99,
        status="0",
    )
    assert resp.get("code") == 200, f"前置新增角色失败: {resp}"
    role_id = fetch_role_id_by_role_key(role_key)
    assert role_id is not None, f"DB 中未找到 roleKey={role_key}"
    return role_id, role_key


# ==============================================================================
# 测试类：数据权限
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("角色管理")
class TestRoleDataScope:
    """角色数据权限接口 PUT /system/role/dataScope 测试集合。"""

    # ==================================================================
    # TC-SYS-ROL-020：修改为全部数据
    # ==================================================================

    @allure.story("修改数据权限")
    @allure.title("TC-SYS-ROL-020：修改数据权限为'全部数据'(dataScope='1')，断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_update_data_scope_all(self) -> None:
        """
        将角色数据权限设置为全部数据（dataScope="1"），断言:
        - 响应 code == 200
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_id, role_key = _create_test_role(role_api)

        try:
            with allure.step(f"修改角色 role_id={role_id} 数据权限为 dataScope='1'（全部数据）"):
                resp = role_api.update_data_scope(role_id=role_id, data_scope="1")

            with allure.step("附加响应"):
                allure.attach(
                    body=str(resp),
                    name="DataScope All Response",
                    attachment_type=allure.attachment_type.TEXT,
                )

            with allure.step("断言 code == 200"):
                assert resp.get("code") == 200, (
                    f"修改数据权限失败: code={resp.get('code')}, msg={resp.get('msg')}"
                )
        finally:
            with allure.step("清理：删除测试角色"):
                role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-021：修改为本部门
    # ==================================================================

    @allure.story("修改数据权限")
    @allure.title("TC-SYS-ROL-021：修改数据权限为'本部门'(dataScope='3')，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_data_scope_dept_only(self) -> None:
        """将角色数据权限设置为本部门（dataScope="3"），断言 code==200。"""
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_id, role_key = _create_test_role(role_api)

        try:
            with allure.step(f"修改 role_id={role_id} dataScope='3'（本部门）"):
                resp = role_api.update_data_scope(role_id=role_id, data_scope="3")

            with allure.step("断言 code == 200"):
                assert resp.get("code") == 200, (
                    f"修改失败: code={resp.get('code')}, msg={resp.get('msg')}"
                )
        finally:
            role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-022：修改为仅本人
    # ==================================================================

    @allure.story("修改数据权限")
    @allure.title("TC-SYS-ROL-022：修改数据权限为'仅本人'(dataScope='5')，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_data_scope_self_only(self) -> None:
        """将角色数据权限设置为仅本人（dataScope="5"），断言 code==200。"""
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_id, role_key = _create_test_role(role_api)

        try:
            with allure.step(f"修改 role_id={role_id} dataScope='5'（仅本人）"):
                resp = role_api.update_data_scope(role_id=role_id, data_scope="5")

            with allure.step("断言 code == 200"):
                assert resp.get("code") == 200, (
                    f"修改失败: code={resp.get('code')}, msg={resp.get('msg')}"
                )
        finally:
            role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-023：数据驱动 dataScope 枚举
    # ==================================================================

    @allure.story("修改数据权限")
    @allure.title("TC-SYS-ROL-023：数据驱动—dataScope 枚举 1~5 均可修改成功")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("data_scope,desc", [
        ("1", "全部数据"),
        ("2", "自定义"),
        ("3", "本部门"),
        ("4", "本部门及以下"),
        ("5", "仅本人"),
    ])
    def test_update_data_scope_parametrize(self, data_scope: str, desc: str) -> None:
        """
        对 dataScope 1~5 逐一验证（数据驱动）：
        - dataScope="2"（自定义）不传 deptIds，服务端按空部门处理。
        - 断言每种枚举 code==200。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_id, role_key = _create_test_role(role_api)

        try:
            with allure.step(f"修改 dataScope='{data_scope}'（{desc}）"):
                resp = role_api.update_data_scope(role_id=role_id, data_scope=data_scope)

            allure.attach(
                body=str(resp),
                name=f"DataScope {data_scope} Response",
                attachment_type=allure.attachment_type.TEXT,
            )

            with allure.step("断言 code == 200"):
                assert resp.get("code") == 200, (
                    f"dataScope='{data_scope}'（{desc}）修改失败: "
                    f"code={resp.get('code')}, msg={resp.get('msg')}"
                )
        finally:
            role_api.delete_roles([role_id])


# ==============================================================================
# 测试类：状态变更
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("角色管理")
class TestRoleStatus:
    """角色状态接口 PUT /system/role/changeStatus 测试集合。"""

    # ==================================================================
    # TC-SYS-ROL-024：停用角色
    # ==================================================================

    @allure.story("角色状态修改")
    @allure.title("TC-SYS-ROL-024：停用角色（status='1'），断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_change_status_disable(self) -> None:
        """
        将正常角色状态改为停用，断言:
        - 响应 code == 200
        - 再次查详情确认 status == "1"
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_id, role_key = _create_test_role(role_api)

        try:
            with allure.step(f"将 role_id={role_id} 状态改为停用（status='1'）"):
                resp = role_api.change_status(role_id=role_id, status="1")

            with allure.step("附加响应"):
                allure.attach(
                    body=str(resp),
                    name="ChangeStatus Disable Response",
                    attachment_type=allure.attachment_type.TEXT,
                )

            with allure.step("断言 code == 200"):
                assert resp.get("code") == 200, (
                    f"停用角色失败: code={resp.get('code')}, msg={resp.get('msg')}"
                )

            with allure.step("查详情确认 status 已变为 '1'"):
                resp_detail = role_api.get_role(role_id)
                actual_status = resp_detail.get("data", {}).get("status")
                assert actual_status == "1", (
                    f"status 未变更: 期望 '1'，实际 {actual_status!r}"
                )
        finally:
            with allure.step("清理：删除测试角色"):
                role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-025：启用角色
    # ==================================================================

    @allure.story("角色状态修改")
    @allure.title("TC-SYS-ROL-025：先停用后启用角色（status='0'），断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_change_status_enable(self) -> None:
        """
        先停用，再启用，断言:
        - 两次操作 code 均 == 200
        - 最终详情 status == "0"
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_id, role_key = _create_test_role(role_api)

        try:
            with allure.step(f"先停用 role_id={role_id}（status='1'）"):
                resp_disable = role_api.change_status(role_id=role_id, status="1")
                assert resp_disable.get("code") == 200, f"停用失败: {resp_disable}"

            with allure.step(f"再启用 role_id={role_id}（status='0'）"):
                resp_enable = role_api.change_status(role_id=role_id, status="0")

            with allure.step("附加启用响应"):
                allure.attach(
                    body=str(resp_enable),
                    name="ChangeStatus Enable Response",
                    attachment_type=allure.attachment_type.TEXT,
                )

            with allure.step("断言启用 code == 200"):
                assert resp_enable.get("code") == 200, (
                    f"启用失败: code={resp_enable.get('code')}, msg={resp_enable.get('msg')}"
                )

            with allure.step("查详情确认 status == '0'"):
                resp_detail = role_api.get_role(role_id)
                actual_status = resp_detail.get("data", {}).get("status")
                assert actual_status == "0", (
                    f"status 未恢复: 期望 '0'，实际 {actual_status!r}"
                )
        finally:
            role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-026：未携带 Token 修改状态
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-ROL-026：未携带 Token 修改角色状态，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_change_status_without_token(self) -> None:
        """
        不注入 Token 直接修改状态，断言:
        - 响应 code != 200（通常为 401）
        """
        role_api = SystemRoleAPI()

        with allure.step("不注入 Token，调用修改状态接口（roleId=1）"):
            resp = role_api.change_status(role_id=1, status="0")

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token ChangeStatus Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

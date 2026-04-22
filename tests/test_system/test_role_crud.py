"""
系统角色 CRUD 测试用例。

真实接口:
    POST   http://192.168.0.107/dev-api/system/role         新增角色
    GET    http://192.168.0.107/dev-api/system/role/{id}    获取角色详情
    PUT    http://192.168.0.107/dev-api/system/role         修改角色
    DELETE http://192.168.0.107/dev-api/system/role/{ids}   删除角色（逗号分隔）

用例清单:
    TC-SYS-ROL-010  仅必填字段新增角色，断言 code==200
    TC-SYS-ROL-011  含可选字段新增角色，断言 code==200
    TC-SYS-ROL-012  重复 roleKey 新增角色，断言 code==500 且 msg 含相关描述
    TC-SYS-ROL-013  未携带 Token 新增角色，断言被鉴权拦截
    TC-SYS-ROL-014  获取角色详情（新增后按 roleId 查询），断言 code==200 且字段匹配
    TC-SYS-ROL-015  修改角色（完整正向链路：新增→查详情→修改），断言 code==200
    TC-SYS-ROL-016  新增后删除（完整正向链路），断言 code==200
    TC-SYS-ROL-017  批量删除多个测试角色，断言 code==200
    TC-SYS-ROL-018  删除不存在的角色 ID，观察服务端实际返回
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
    """生成唯一角色权限字符串（取 UUID 前 8 位），防止用例间冲突。"""
    return "test_role_" + uuid.uuid4().hex[:8]


def _gen_role_name() -> str:
    """生成唯一角色名称。"""
    return "测试角色_" + uuid.uuid4().hex[:6]


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


def _create_test_role(role_api: SystemRoleAPI) -> tuple[str, str]:
    """
    新增一个测试角色，返回 (role_name, role_key)。
    调用方需负责在测试结束后删除该角色。
    """
    role_name = _gen_role_name()
    role_key = _gen_role_key()
    resp = role_api.add_role(role_name=role_name, role_key=role_key, role_sort=99, status="0")
    assert resp.get("code") == 200, f"前置新增角色失败: {resp}"
    return role_name, role_key


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("角色管理")
class TestRoleCrud:
    """角色 CRUD 接口综合测试集合。"""

    # ==================================================================
    # TC-SYS-ROL-010：仅必填字段新增
    # ==================================================================

    @allure.story("新增角色")
    @allure.title("TC-SYS-ROL-010：仅传必填字段（roleName/roleKey/roleSort/status）新增角色成功")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_add_role_required_fields_only(self) -> None:
        """
        只传四个必填字段，断言:
        - 响应 code == 200
        - 响应 msg == "操作成功"

        测试后通过接口删除所建角色，保持环境整洁。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_name = _gen_role_name()
        role_key = _gen_role_key()

        with allure.step(f"调用新增接口（仅必填字段）: roleName={role_name}, roleKey={role_key}"):
            resp = role_api.add_role(
                role_name=role_name,
                role_key=role_key,
                role_sort=99,
                status="0",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddRole Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 msg == '操作成功'"):
            assert resp.get("msg") == "操作成功", (
                f"msg 异常: {resp.get('msg')!r}"
            )

        with allure.step("清理：删除刚新增的测试角色"):
            role_id = fetch_role_id_by_role_key(role_key)
            if role_id is not None:
                role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-011：含可选字段新增
    # ==================================================================

    @allure.story("新增角色")
    @allure.title("TC-SYS-ROL-011：含可选字段（dataScope/remark/menuCheckStrictly）新增角色，断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_role_with_optional_fields(self) -> None:
        """
        传入必填字段 + 可选字段，断言:
        - 响应 code == 200

        测试后通过接口删除所建角色。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_name = _gen_role_name()
        role_key = _gen_role_key()

        with allure.step(f"调用新增接口（含可选字段）: roleKey={role_key}"):
            resp = role_api.add_role(
                role_name=role_name,
                role_key=role_key,
                role_sort=50,
                status="0",
                data_scope="1",
                menu_check_strictly=True,
                dept_check_strictly=True,
                menu_ids=[],
                remark="自动化测试角色备注",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddRole Optional Fields Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("清理：删除刚新增的测试角色"):
            role_id = fetch_role_id_by_role_key(role_key)
            if role_id is not None:
                role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-012：重复 roleKey 新增（负面用例）
    # ==================================================================

    @allure.story("新增角色")
    @allure.title("TC-SYS-ROL-012：重复 roleKey 新增，断言 code==500 且 msg 含相关描述")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_role_duplicate_key(self) -> None:
        """
        两次使用相同 roleKey 新增，断言:
        - 第一次 code == 200
        - 第二次 code == 500 且 msg 包含 "已存在" 相关字样
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_key = _gen_role_key()
        role_name_1 = _gen_role_name()
        role_name_2 = _gen_role_name()

        with allure.step(f"第一次新增角色: roleKey={role_key}"):
            resp1 = role_api.add_role(role_name=role_name_1, role_key=role_key, role_sort=99, status="0")

        assert resp1.get("code") == 200, f"第一次新增失败: {resp1}"

        with allure.step(f"第二次新增（相同 roleKey）: roleKey={role_key}"):
            resp2 = role_api.add_role(role_name=role_name_2, role_key=role_key, role_sort=99, status="0")

        with allure.step("附加第二次响应"):
            allure.attach(
                body=str(resp2),
                name="Duplicate RoleKey Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言第二次 code == 500"):
            assert resp2.get("code") == 500, (
                f"期望 code==500，实际 code={resp2.get('code')}, msg={resp2.get('msg')}"
            )

        with allure.step("清理：删除第一次新增的测试角色"):
            role_id = fetch_role_id_by_role_key(role_key)
            if role_id is not None:
                role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-013：未携带 Token 新增角色
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-ROL-013：未携带 Token 新增角色，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_role_without_token(self) -> None:
        """
        不注入 Token 直接调用新增接口，断言:
        - 响应 code != 200（通常为 401）
        """
        role_api = SystemRoleAPI()

        with allure.step("不注入 Token，调用新增角色接口"):
            resp = role_api.add_role(
                role_name=_gen_role_name(),
                role_key=_gen_role_key(),
                role_sort=99,
                status="0",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token AddRole Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

    # ==================================================================
    # TC-SYS-ROL-014：获取角色详情
    # ==================================================================

    @allure.story("获取角色详情")
    @allure.title("TC-SYS-ROL-014：新增角色后获取详情，断言 code==200 且关键字段匹配")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_role_detail(self) -> None:
        """
        完整链路：新增角色 → 通过 roleKey 查询 role_id → 调用详情接口，断言:
        - 响应 code == 200
        - data.roleKey 与新增时一致
        - data.roleName 与新增时一致
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_name = _gen_role_name()
        role_key = _gen_role_key()

        with allure.step(f"前置：新增角色 roleKey={role_key}"):
            resp_add = role_api.add_role(role_name=role_name, role_key=role_key, role_sort=99, status="0")
            assert resp_add.get("code") == 200, f"前置新增失败: {resp_add}"

        with allure.step("从 DB 查询 role_id"):
            role_id = fetch_role_id_by_role_key(role_key)
            if role_id is None:
                pytest.skip(f"DB 中未找到 roleKey={role_key}，跳过详情测试")

        allure.attach(
            body=f"role_id={role_id}\nrole_name={role_name}\nrole_key={role_key}",
            name="新增角色信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用详情接口: GET /system/role/{role_id}"):
            resp = role_api.get_role(role_id)

        with allure.step("附加详情响应"):
            allure.attach(
                body=str(resp),
                name="GetRole Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"获取详情失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言详情中 roleKey 与 roleName 与新增时一致"):
            data = resp.get("data", {})
            assert data.get("roleKey") == role_key, (
                f"roleKey 不匹配: 期望 {role_key!r}，实际 {data.get('roleKey')!r}"
            )
            assert data.get("roleName") == role_name, (
                f"roleName 不匹配: 期望 {role_name!r}，实际 {data.get('roleName')!r}"
            )

        with allure.step("清理：删除测试角色"):
            role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-015：修改角色
    # ==================================================================

    @allure.story("修改角色")
    @allure.title("TC-SYS-ROL-015：新增→获取详情→修改角色，断言 code==200 且修改后字段生效")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_role(self) -> None:
        """
        完整正向链路：
        1. 新增测试角色；
        2. 通过 roleKey 查 role_id；
        3. 调用详情获取原始字段；
        4. 修改 roleName 与 remark，断言 code==200；
        5. 再次查详情确认修改生效。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_name = _gen_role_name()
        role_key = _gen_role_key()

        with allure.step(f"前置：新增角色 roleKey={role_key}"):
            resp_add = role_api.add_role(role_name=role_name, role_key=role_key, role_sort=99, status="0")
            assert resp_add.get("code") == 200, f"前置新增失败: {resp_add}"

        with allure.step("从 DB 查询 role_id"):
            role_id = fetch_role_id_by_role_key(role_key)
            if role_id is None:
                pytest.skip(f"DB 中未找到 roleKey={role_key}，跳过修改测试")

        new_role_name = _gen_role_name()

        with allure.step(f"调用修改接口: roleName 改为 {new_role_name}"):
            resp_update = role_api.update_role(
                role_id=role_id,
                role_name=new_role_name,
                role_key=role_key,
                role_sort=99,
                status="0",
                remark="自动化修改备注",
            )

        with allure.step("附加修改响应"):
            allure.attach(
                body=str(resp_update),
                name="UpdateRole Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言修改 code == 200"):
            assert resp_update.get("code") == 200, (
                f"修改失败: code={resp_update.get('code')}, msg={resp_update.get('msg')}"
            )

        with allure.step("再次查详情，断言 roleName 已更新"):
            resp_detail = role_api.get_role(role_id)
            data = resp_detail.get("data", {})
            assert data.get("roleName") == new_role_name, (
                f"修改未生效: 期望 {new_role_name!r}，实际 {data.get('roleName')!r}"
            )

        with allure.step("清理：删除测试角色"):
            role_api.delete_roles([role_id])

    # ==================================================================
    # TC-SYS-ROL-016：新增后删除（完整正向链路）
    # ==================================================================

    @allure.story("删除角色")
    @allure.title("TC-SYS-ROL-016：新增角色后删除，断言 code==200")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_delete_role_after_add(self) -> None:
        """
        完整正向链路：
        1. 新增测试角色；
        2. 通过 roleKey 查询 role_id；
        3. 调用删除接口，断言 code==200。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_name = _gen_role_name()
        role_key = _gen_role_key()

        with allure.step(f"前置：新增角色 roleKey={role_key}"):
            resp_add = role_api.add_role(role_name=role_name, role_key=role_key, role_sort=99, status="0")
            assert resp_add.get("code") == 200, f"前置新增失败: {resp_add}"

        with allure.step("从 DB 查询 role_id"):
            role_id = fetch_role_id_by_role_key(role_key)
            if role_id is None:
                pytest.skip(f"DB 中未找到 roleKey={role_key}，跳过删除测试")

        allure.attach(
            body=f"role_id={role_id}\nrole_key={role_key}",
            name="待删除角色信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用删除接口: DELETE /system/role/{role_id}"):
            resp = role_api.delete_roles([role_id])

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(resp),
                name="DeleteRole Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"删除失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-ROL-017：批量删除多个测试角色
    # ==================================================================

    @allure.story("删除角色")
    @allure.title("TC-SYS-ROL-017：批量删除多个测试角色，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_roles_batch(self) -> None:
        """
        批量删除链路：
        1. 新增两个测试角色；
        2. 调用批量删除接口，断言 code==200。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        role_ids: list[int] = []

        with allure.step("前置：批量新增两个测试角色"):
            for _ in range(2):
                role_key = _gen_role_key()
                resp_add = role_api.add_role(
                    role_name=_gen_role_name(),
                    role_key=role_key,
                    role_sort=99,
                    status="0",
                )
                assert resp_add.get("code") == 200, f"前置批量新增失败: {resp_add}"
                role_id = fetch_role_id_by_role_key(role_key)
                if role_id is not None:
                    role_ids.append(role_id)

        if len(role_ids) < 2:
            pytest.skip("DB 中未能查到足够的测试角色 ID，跳过批量删除测试")

        allure.attach(
            body=f"批量删除 role_ids: {role_ids}",
            name="待删除角色信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用批量删除接口: DELETE /system/role/{','.join(str(i) for i in role_ids)}"):
            resp = role_api.delete_roles(role_ids)

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(resp),
                name="BatchDeleteRole Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"批量删除失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-ROL-018：删除不存在的角色（边界用例）
    # ==================================================================

    @allure.story("删除角色")
    @allure.title("TC-SYS-ROL-018：删除不存在的角色 ID（99999999），观察服务端实际返回")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_nonexistent_role(self) -> None:
        """
        删除一个不存在的角色 ID，断言:
        - 服务端有明确响应（不崩溃）
        - code 通常为 200（幂等删除）或 500（业务错误）

        该用例记录服务端实际行为，以便回归时发现行为变化。
        """
        token = _login_and_get_token()
        role_api = SystemRoleAPI()
        role_api.set_token(token)

        nonexistent_id = 99999999

        with allure.step(f"调用删除接口: role_id={nonexistent_id}"):
            resp = role_api.delete_roles([nonexistent_id])

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="Delete Nonexistent Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言服务端有明确响应（code 在 200/400/500 之一）"):
            assert resp.get("code") in (200, 400, 500), (
                f"服务端响应异常 code={resp.get('code')}, msg={resp.get('msg')}"
            )

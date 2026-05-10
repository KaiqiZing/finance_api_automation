"""
系统权限与组织约束补充用例。

覆盖:
    - 非 admin 低权限用户访问无权限接口应被拒绝
    - 用户停用后登录应失败
    - 自定义数据权限 dataScope=2 写入角色-部门关系
    - 角色菜单权限应进入普通用户 getInfo.permissions
    - 父部门存在子部门时禁止删除父部门
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import allure
import pytest

from api.system.dept_api import SystemDeptAPI
from api.system.login_api import SystemLoginAPI
from api.system.role_api import SystemRoleAPI
from api.system.user_api import SystemUserAPI
from core.validator import Validator
from tests.test_system.conftest import _login_and_get_token, gen_phone, gen_username
from utils.db_client import DBClient
from utils.logger import logger
from utils.system_ruoyi_queries import (
    fetch_dept_id_by_dept_name,
    fetch_random_third_level_dept_id,
    fetch_role_id_by_role_key,
    purge_sys_user_bindings,
)


ROOT_DEPT_ID = 100
TEST_PASSWORD = "Test@123456"
MENU_PERMISSION_USER_LIST = "system:user:list"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _role_key() -> str:
    return f"rbac_role_{_uid()}"


def _role_name() -> str:
    return f"RBAC测试角色_{_uid()}"


def _dept_name() -> str:
    return f"RBAC测试部门_{_uid()}"


def _attach_json(name: str, data: Any) -> None:
    allure.attach(
        body=json.dumps(data, ensure_ascii=False, indent=2, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def _admin_apis() -> tuple[SystemUserAPI, SystemRoleAPI, SystemDeptAPI]:
    token = _login_and_get_token()
    user_api = SystemUserAPI()
    role_api = SystemRoleAPI()
    dept_api = SystemDeptAPI()
    for api in (user_api, role_api, dept_api):
        api.set_token(token)
    return user_api, role_api, dept_api


def _login_token(username: str, password: str = TEST_PASSWORD) -> str:
    resp = SystemLoginAPI().login(username=username, password=password)
    assert resp.get("code") == 200, f"登录失败: {resp}"
    return resp["data"]["access_token"]


def _query_user(username: str) -> dict[str, Any] | None:
    return DBClient.instance("ry_cloud").fetch_one(
        "SELECT user_id, user_name, dept_id, status, del_flag "
        "FROM sys_user WHERE user_name = %s AND del_flag = '0' LIMIT 1",
        (username,),
    )


def _fetch_menu_id_by_perm(perms: str) -> int | None:
    row = DBClient.instance("ry_cloud").fetch_one(
        "SELECT menu_id FROM sys_menu "
        "WHERE perms = %s AND status = '0' AND menu_type IN ('C', 'F') "
        "ORDER BY menu_id ASC LIMIT 1",
        (perms,),
    )
    return int(row["menu_id"]) if row else None


def _create_role(
    role_api: SystemRoleAPI,
    *,
    menu_ids: list[int] | None = None,
    data_scope: str = "1",
) -> int:
    role_key = _role_key()
    resp = role_api.add_role(
        role_name=_role_name(),
        role_key=role_key,
        role_sort=99,
        status="0",
        data_scope=data_scope,
        menu_ids=menu_ids or [],
        remark="RBAC 自动化测试角色",
    )
    Validator.assert_ruoyi_success(resp)
    role_id = fetch_role_id_by_role_key(role_key)
    assert role_id is not None, f"新增角色后 DB 未找到 role_key={role_key}"
    return role_id


def _create_user(
    user_api: SystemUserAPI,
    *,
    dept_id: int,
    role_ids: list[int],
    status: str = "0",
) -> tuple[str, int]:
    username = gen_username()
    resp = user_api.add_user(
        user_name=username,
        nick_name=f"RBAC用户{_uid()}",
        password=TEST_PASSWORD,
        phonenumber=gen_phone(),
        email=f"{username}@test.com",
        status=status,
        dept_id=dept_id,
        role_ids=role_ids,
        post_ids=[],
        remark="RBAC 自动化测试用户",
    )
    Validator.assert_ruoyi_success(resp)
    row = _query_user(username)
    assert row is not None, f"新增用户后 DB 未找到 user_name={username}"
    return username, int(row["user_id"])


def _cleanup_user(user_api: SystemUserAPI, user_id: int | None) -> None:
    if user_id is None:
        return
    try:
        user_api.delete_user(user_id)
    except Exception as exc:
        logger.warning("[RBAC] 清理用户失败 user_id={} err={}", user_id, exc)
    purge_sys_user_bindings(user_id)


def _cleanup_role(role_api: SystemRoleAPI, role_id: int | None) -> None:
    if role_id is None:
        return
    try:
        role_api.delete_roles([role_id])
    except Exception as exc:
        logger.warning("[RBAC] 清理角色失败 role_id={} err={}", role_id, exc)


def _cleanup_dept(dept_api: SystemDeptAPI, dept_id: int | None) -> None:
    if dept_id is None:
        return
    try:
        dept_api.delete_dept(dept_id)
    except Exception as exc:
        logger.warning("[RBAC] 清理部门失败 dept_id={} err={}", dept_id, exc)


@allure.epic("系统管理模块")
@allure.feature("权限与组织约束")
class TestPermissionRbac:
    """补齐权限、用户状态、数据权限和部门结构约束场景。"""

    @allure.story("非 admin 权限")
    @allure.title("TC-SYS-RBAC-001：低权限用户访问用户列表应被拒绝")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_non_admin_without_user_list_permission_is_rejected(self) -> None:
        user_api, role_api, _dept_api = _admin_apis()
        role_id: int | None = None
        user_id: int | None = None

        try:
            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门，跳过低权限用例")
            role_id = _create_role(role_api, menu_ids=[])
            username, user_id = _create_user(user_api, dept_id=dept_id, role_ids=[role_id])

            low_user_api = SystemUserAPI()
            low_user_api.set_token(_login_token(username))
            resp = low_user_api.list_users(page_num=1, page_size=10)
            _attach_json("低权限用户访问用户列表响应", resp)

            assert resp.get("code") != 200, f"低权限用户不应能访问用户列表: {resp}"
        finally:
            _cleanup_user(user_api, user_id)
            _cleanup_role(role_api, role_id)

    @allure.story("用户状态")
    @allure.title("TC-SYS-RBAC-002：停用用户再次登录应失败")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_disabled_user_login_is_rejected(self) -> None:
        user_api, role_api, _dept_api = _admin_apis()
        role_id: int | None = None
        user_id: int | None = None

        try:
            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门，跳过停用用户用例")
            role_id = _create_role(role_api)
            username, user_id = _create_user(user_api, dept_id=dept_id, role_ids=[role_id])

            resp = user_api.update_user(
                user_id=user_id,
                dept_id=dept_id,
                user_name=username,
                status="1",
                role_ids=[role_id],
                post_ids=[],
            )
            Validator.assert_ruoyi_success(resp)

            login_resp = SystemLoginAPI().login(username=username, password=TEST_PASSWORD)
            _attach_json("停用用户登录响应", login_resp)
            assert login_resp.get("code") != 200, f"停用用户不应登录成功: {login_resp}"
        finally:
            _cleanup_user(user_api, user_id)
            _cleanup_role(role_api, role_id)

    @allure.story("数据权限")
    @allure.title("TC-SYS-RBAC-003：自定义数据权限 dataScope=2 写入角色部门关系")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_custom_data_scope_persists_role_depts(self) -> None:
        _user_api, role_api, _dept_api = _admin_apis()
        role_id: int | None = None

        try:
            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门，跳过数据权限用例")
            role_id = _create_role(role_api)

            resp = role_api.update_data_scope(role_id=role_id, data_scope="2", dept_ids=[dept_id])
            Validator.assert_ruoyi_success(resp)

            row = DBClient.instance("ry_cloud").fetch_one(
                "SELECT data_scope FROM sys_role WHERE role_id = %s AND del_flag = '0' LIMIT 1",
                (role_id,),
            )
            links = DBClient.instance("ry_cloud").fetch_all(
                "SELECT dept_id FROM sys_role_dept WHERE role_id = %s ORDER BY dept_id ASC",
                (role_id,),
            )
            detail = role_api.get_role(role_id)
            _attach_json("自定义数据权限 DB 与详情", {"role": row, "links": links, "detail": detail})

            assert row and row.get("data_scope") == "2", f"角色 data_scope 未更新为 2: {row}"
            assert dept_id in [int(item["dept_id"]) for item in links], (
                f"sys_role_dept 未写入 dept_id={dept_id}: {links}"
            )
            detail_dept_ids = detail.get("data", {}).get("deptIds")
            if detail_dept_ids:
                assert dept_id in detail_dept_ids, f"角色详情 deptIds 不含 {dept_id}: {detail}"
        finally:
            _cleanup_role(role_api, role_id)

    @allure.story("角色菜单权限")
    @allure.title("TC-SYS-RBAC-004：分配菜单后普通用户 getInfo.permissions 包含对应权限")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_role_menu_permission_appears_in_get_info(self) -> None:
        user_api, role_api, _dept_api = _admin_apis()
        role_id: int | None = None
        user_id: int | None = None

        try:
            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门，跳过菜单权限用例")
            menu_id = _fetch_menu_id_by_perm(MENU_PERMISSION_USER_LIST)
            if menu_id is None:
                pytest.skip(f"sys_menu 中未找到权限标识 {MENU_PERMISSION_USER_LIST}")

            role_id = _create_role(role_api, menu_ids=[menu_id])
            username, user_id = _create_user(user_api, dept_id=dept_id, role_ids=[role_id])

            current_user_api = SystemUserAPI()
            current_user_api.set_token(_login_token(username))
            info_resp = current_user_api.get_info()
            _attach_json("普通用户 getInfo 响应", info_resp)

            Validator.assert_ruoyi_success(info_resp)
            permissions = info_resp.get("permissions", [])
            assert MENU_PERMISSION_USER_LIST in permissions, (
                f"permissions 未包含 {MENU_PERMISSION_USER_LIST}: {permissions}"
            )
        finally:
            _cleanup_user(user_api, user_id)
            _cleanup_role(role_api, role_id)

    @allure.story("部门父子约束")
    @allure.title("TC-SYS-RBAC-005：父部门存在子部门时删除父部门应失败")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_parent_dept_with_child_is_rejected(self) -> None:
        _user_api, _role_api, dept_api = _admin_apis()
        parent_id: int | None = None
        child_id: int | None = None

        try:
            parent_name = _dept_name()
            child_name = _dept_name()
            resp = dept_api.add_dept(
                parent_id=ROOT_DEPT_ID,
                dept_name=parent_name,
                order_num=998,
            )
            Validator.assert_ruoyi_success(resp)
            parent_id = fetch_dept_id_by_dept_name(parent_name, ROOT_DEPT_ID)
            assert parent_id is not None, f"新增父部门后 DB 未找到 deptName={parent_name}"

            resp = dept_api.add_dept(
                parent_id=parent_id,
                dept_name=child_name,
                order_num=999,
            )
            Validator.assert_ruoyi_success(resp)
            child_id = fetch_dept_id_by_dept_name(child_name, parent_id)
            assert child_id is not None, f"新增子部门后 DB 未找到 deptName={child_name}"

            delete_resp = dept_api.delete_dept(parent_id)
            _attach_json("删除存在子部门的父部门响应", delete_resp)
            assert delete_resp.get("code") != 200, f"父部门存在子部门时不应删除成功: {delete_resp}"
            message = str(delete_resp.get("msg") or delete_resp.get("message") or "")
            assert ("子" in message) or ("下级" in message), (
                f"错误信息应提示存在子部门: {delete_resp}"
            )
        finally:
            _cleanup_dept(dept_api, child_id)
            _cleanup_dept(dept_api, parent_id)

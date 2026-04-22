"""
用户-岗位-角色 业务场景联调用例。

依赖: admin 可登录；ry_cloud 库为若依标准表结构（含 sys_user_post / sys_user_role）。

场景:
    TC-SYS-FLW-001  新增岗位 → 新增角色 → 用二者新增用户，回查关联表后清理
    TC-SYS-FLW-002  新增岗位 → 新增角色 → 先新增用户再改为绑定新岗位/新角色
    TC-SYS-FLW-003  用户已绑定岗位时删除岗位被后端拒绝（已分配不能删），断言关联仍存在；
                    收尾：删用户并 purge 关联表后再删岗位/角色
    TC-SYS-FLW-004  用户已绑定角色时删除角色被后端拒绝（已分配不能删），断言关联仍存在；
                    收尾：删用户并 purge 关联表后再删角色/岗位
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.post_api import SystemPostAPI
from api.system.role_api import SystemRoleAPI
from api.system.user_api import SystemUserAPI
from utils.db_client import DBClient
from utils.system_ruoyi_queries import (
    count_sys_user_post_link,
    count_sys_user_role_link,
    fetch_post_id_by_post_code,
    fetch_random_third_level_dept_id,
    fetch_role_id_by_role_key,
    purge_sys_user_bindings,
)


def _gen_username() -> str:
    return "test_" + uuid.uuid4().hex[:8]


def _gen_post_code() -> str:
    return "test_" + uuid.uuid4().hex[:8]


def _gen_post_name() -> str:
    return "测试岗位_" + uuid.uuid4().hex[:6]


def _gen_role_key() -> str:
    return "test_role_" + uuid.uuid4().hex[:8]


def _gen_role_name() -> str:
    return "测试角色_" + uuid.uuid4().hex[:6]


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败: {resp}"
    return resp["data"]["access_token"]


def _user_id_by_name(username: str) -> int | None:
    row = DBClient.instance("ry_cloud").fetch_one(
        "SELECT user_id FROM sys_user WHERE user_name = %s AND del_flag = '0' LIMIT 1",
        (username,),
    )
    return int(row["user_id"]) if row else None


def _cleanup_post_role_user(
    user_api: SystemUserAPI,
    role_api: SystemRoleAPI,
    post_api: SystemPostAPI,
    user_id: int | None,
    role_id: int | None,
    post_id: int | None,
) -> None:
    """
    逆序释放测试数据。若依逻辑删除用户后可能仍残留 sys_user_* 关联，
    会导致 delete_roles 报「已分配,不能删除」，故在删角色/岗位前 purge。
    """
    if user_id is not None:
        user_api.delete_user(user_id)
        purge_sys_user_bindings(user_id)
    if role_id is not None:
        role_api.delete_roles([role_id])
    if post_id is not None:
        post_api.delete_posts([post_id])


@allure.epic("系统管理模块")
@allure.feature("用户-岗位-角色业务场景")
class TestUserPostRoleBusinessFlow:
    """岗位 / 角色 / 用户 串联业务场景（FLW-004 与若依「已分配不可删角色」行为对齐）。"""

    @allure.story("业务联调")
    @allure.title("TC-SYS-FLW-001：新增岗位与角色后，用二者新增用户并校验关联")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_flow_add_post_role_then_user_with_both(self) -> None:
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        role_api = SystemRoleAPI()
        user_api = SystemUserAPI()
        post_api.set_token(token)
        role_api.set_token(token)
        user_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()
        role_name = _gen_role_name()
        role_key = _gen_role_key()
        post_id: int | None = None
        role_id: int | None = None
        user_id: int | None = None

        try:
            with allure.step("新增岗位"):
                r_post = post_api.add_post(
                    post_name=post_name,
                    post_code=post_code,
                    post_sort=99,
                    status="0",
                )
                assert r_post.get("code") == 200, r_post
                post_id = fetch_post_id_by_post_code(post_code)
                assert post_id is not None, "新增岗位后未查到 post_id"

            with allure.step("新增角色"):
                r_role = role_api.add_role(
                    role_name=role_name,
                    role_key=role_key,
                    role_sort=99,
                    status="0",
                )
                assert r_role.get("code") == 200, r_role
                role_id = fetch_role_id_by_role_key(role_key)
                assert role_id is not None, "新增角色后未查到 role_id"

            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门")

            username = _gen_username()
            with allure.step("新增用户并绑定岗位与角色"):
                r_user = user_api.add_user(
                    user_name=username,
                    nick_name="联调001",
                    password="Test@123456",
                    dept_id=dept_id,
                    role_ids=[role_id],
                    post_ids=[post_id],
                )
                assert r_user.get("code") == 200, r_user

            user_id = _user_id_by_name(username)
            assert user_id is not None, "新增用户后未查到 user_id"

            with allure.step("断言 sys_user_post / sys_user_role 存在关联"):
                assert count_sys_user_post_link(user_id, post_id) >= 1
                assert count_sys_user_role_link(user_id, role_id) >= 1
        finally:
            _cleanup_post_role_user(user_api, role_api, post_api, user_id, role_id, post_id)

    @allure.story("业务联调")
    @allure.title("TC-SYS-FLW-002：新增岗位与角色后，将已有用户改为绑定新岗位与新角色")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_flow_add_post_role_then_update_user_bindings(self) -> None:
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        role_api = SystemRoleAPI()
        user_api = SystemUserAPI()
        post_api.set_token(token)
        role_api.set_token(token)
        user_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()
        role_name = _gen_role_name()
        role_key = _gen_role_key()
        post_id: int | None = None
        role_id: int | None = None
        user_id: int | None = None

        try:
            with allure.step("新增岗位与角色"):
                assert post_api.add_post(
                    post_name=post_name,
                    post_code=post_code,
                    post_sort=99,
                    status="0",
                ).get("code") == 200
                post_id = fetch_post_id_by_post_code(post_code)
                assert post_id is not None

                assert role_api.add_role(
                    role_name=role_name,
                    role_key=role_key,
                    role_sort=99,
                    status="0",
                ).get("code") == 200
                role_id = fetch_role_id_by_role_key(role_key)
                assert role_id is not None

            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门")

            username = _gen_username()
            with allure.step("前置：新增用户（初始不绑定岗位/角色）"):
                assert user_api.add_user(
                    user_name=username,
                    nick_name="联调002",
                    password="Test@123456",
                    dept_id=dept_id,
                    role_ids=[],
                    post_ids=[],
                ).get("code") == 200

            user_id = _user_id_by_name(username)
            assert user_id is not None
            row = DBClient.instance("ry_cloud").fetch_one(
                "SELECT dept_id, user_name FROM sys_user WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            assert row is not None
            dept_db = int(row["dept_id"])
            user_name_db = row["user_name"]

            with allure.step("修改用户：绑定新岗位与新角色"):
                r_upd = user_api.update_user(
                    user_id=user_id,
                    dept_id=dept_db,
                    user_name=user_name_db,
                    role_ids=[role_id],
                    post_ids=[post_id],
                )
                assert r_upd.get("code") == 200, r_upd

            with allure.step("断言关联表已写入"):
                assert count_sys_user_post_link(user_id, post_id) >= 1
                assert count_sys_user_role_link(user_id, role_id) >= 1
        finally:
            _cleanup_post_role_user(user_api, role_api, post_api, user_id, role_id, post_id)

    @allure.story("业务联调")
    @allure.title(
        "TC-SYS-FLW-003：已绑定用户的岗位删除被拦截（已分配不能删），关联仍存在；"
        "删用户并清理关联后可删岗位"
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_flow_delete_post_clears_user_post_link(self) -> None:
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        role_api = SystemRoleAPI()
        user_api = SystemUserAPI()
        post_api.set_token(token)
        role_api.set_token(token)
        user_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()
        role_name = _gen_role_name()
        role_key = _gen_role_key()
        post_id: int | None = None
        role_id: int | None = None
        user_id: int | None = None

        try:
            assert post_api.add_post(
                post_name=post_name,
                post_code=post_code,
                post_sort=99,
                status="0",
            ).get("code") == 200
            post_id = fetch_post_id_by_post_code(post_code)
            assert post_id is not None

            assert role_api.add_role(
                role_name=role_name,
                role_key=role_key,
                role_sort=99,
                status="0",
            ).get("code") == 200
            role_id = fetch_role_id_by_role_key(role_key)
            assert role_id is not None

            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门")

            username = _gen_username()
            assert user_api.add_user(
                user_name=username,
                nick_name="联调003",
                password="Test@123456",
                dept_id=dept_id,
                role_ids=[role_id],
                post_ids=[post_id],
            ).get("code") == 200

            user_id = _user_id_by_name(username)
            assert user_id is not None
            assert count_sys_user_post_link(user_id, post_id) >= 1

            with allure.step("删除岗位（预期：用户仍绑定，接口拒绝）"):
                del_post = post_api.delete_posts([post_id])
                allure.attach(str(del_post), name="DeletePost Response", attachment_type=allure.attachment_type.TEXT)
                assert del_post.get("code") == 500, (
                    f"预期已分配岗位不可删返回 500，实际: {del_post}"
                )
                msg = del_post.get("msg") or ""
                assert "已分配" in msg or "不能删除" in msg, (
                    f"预期 msg 含「已分配」或「不能删除」，实际: {msg!r}"
                )

            with allure.step("断言用户与该岗位的关联仍存在"):
                assert count_sys_user_post_link(user_id, post_id) >= 1
        finally:
            _cleanup_post_role_user(user_api, role_api, post_api, user_id, role_id, post_id)

    @allure.story("业务联调")
    @allure.title(
        "TC-SYS-FLW-004：已绑定用户的角色删除被拦截（已分配不能删），关联仍存在；"
        "删用户并清理关联后可删角色"
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_flow_delete_role_clears_user_role_link(self) -> None:
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        role_api = SystemRoleAPI()
        user_api = SystemUserAPI()
        post_api.set_token(token)
        role_api.set_token(token)
        user_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()
        role_name = _gen_role_name()
        role_key = _gen_role_key()
        post_id: int | None = None
        role_id: int | None = None
        user_id: int | None = None

        try:
            assert post_api.add_post(
                post_name=post_name,
                post_code=post_code,
                post_sort=99,
                status="0",
            ).get("code") == 200
            post_id = fetch_post_id_by_post_code(post_code)
            assert post_id is not None

            assert role_api.add_role(
                role_name=role_name,
                role_key=role_key,
                role_sort=99,
                status="0",
            ).get("code") == 200
            role_id = fetch_role_id_by_role_key(role_key)
            assert role_id is not None

            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                pytest.skip("二级部门 101 下无可用三级子部门")

            username = _gen_username()
            assert user_api.add_user(
                user_name=username,
                nick_name="联调004",
                password="Test@123456",
                dept_id=dept_id,
                role_ids=[role_id],
                post_ids=[post_id],
            ).get("code") == 200

            user_id = _user_id_by_name(username)
            assert user_id is not None
            assert count_sys_user_role_link(user_id, role_id) >= 1

            with allure.step("删除角色（预期：用户仍绑定，接口拒绝）"):
                del_role = role_api.delete_roles([role_id])
                allure.attach(str(del_role), name="DeleteRole Response", attachment_type=allure.attachment_type.TEXT)
                assert del_role.get("code") == 500, (
                    f"预期已分配不可删返回 500，实际: {del_role}"
                )
                msg = del_role.get("msg") or ""
                assert "已分配" in msg or "不能删除" in msg, (
                    f"预期 msg 含「已分配」或「不能删除」，实际: {msg!r}"
                )

            with allure.step("断言用户与该角色的关联仍存在"):
                assert count_sys_user_role_link(user_id, role_id) >= 1
        finally:
            _cleanup_post_role_user(user_api, role_api, post_api, user_id, role_id, post_id)

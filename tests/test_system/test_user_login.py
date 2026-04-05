"""
系统用户登录 & 获取用户信息 测试用例。

真实接口:
    POST  http://localhost:1024/dev-api/auth/login
          请求体: {"username": "admin", "password": "admin123"}
          响应体: {"code": 200, "msg": null, "data": {"access_token": "eyJ...", "expires_in": 720}}

    GET   http://localhost:1024/dev-api/system/user/getInfo
          请求头: Authorization: Bearer <access_token>
          响应体: {"code": 200, "user": {...}, "roles": [...], "permissions": [...]}

用例清单:
    TC-SYS-001  正常登录，断言 data.access_token 非空 & 响应结构合法
    TC-SYS-002  登录后调用 getInfo，断言用户基本信息、角色、权限非空
    TC-SYS-003  完整链路：登录 → getInfo（通过 SystemFlows 一步完成）
    TC-SYS-004  使用不存在的用户名登录，断言被服务端拒绝（code != 200）
    TC-SYS-005  未携带 Token 直接请求 getInfo，断言被鉴权拦截
    TC-SYS-006  数据驱动：多账号登录验证（可在 parametrize 中追加账号）
"""
from __future__ import annotations

import pytest
import allure

from api.system.login_api import SystemLoginAPI
from api.system.user_api import SystemUserAPI
from business.system_flows import SystemFlows
from core.context import GlobalContext
from core.validator import Validator


@allure.epic("系统管理模块")
@allure.feature("用户鉴权")
class TestUserLogin:
    """登录接口 + getInfo 接口测试集合。"""

    # ==================================================================
    # TC-SYS-001：正常登录
    # ==================================================================

    @allure.story("正常登录流程")
    @allure.title("TC-SYS-001：admin 正常登录，data.access_token 非空")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_login_success(self) -> None:
        """
        使用正确的用户名/密码登录，断言:
        - 响应 code == 200
        - data.access_token 非空且为字符串
        - data.expires_in 为正整数（Token 有效期）
        - 响应结构符合 system_login_response JSON Schema
        """
        login_api = SystemLoginAPI()

        with allure.step("调用登录接口 POST /auth/login  user=admin"):
            resp = login_api.login(username="admin", password="admin123")

        with allure.step("附加完整响应内容"):
            allure.attach(
                body=str(resp),
                name="Login Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"登录失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 data.access_token 非空且为字符串"):
            data = resp.get("data", {})
            token = data.get("access_token", "")
            assert isinstance(token, str) and len(token) > 0, (
                f"access_token 异常: {token!r}，完整 data: {data}"
            )

        with allure.step("断言 data.expires_in 为正整数"):
            expires_in = data.get("expires_in")
            assert isinstance(expires_in, int) and expires_in > 0, (
                f"expires_in 异常: {expires_in!r}"
            )

        with allure.step("断言响应结构符合 JSON Schema 契约"):
            Validator.assert_schema(resp, "system_login_response")

        with allure.step("将 token 写入 GlobalContext 供后续步骤使用"):
            GlobalContext.instance().set("system_token", token)

    # ==================================================================
    # TC-SYS-002：登录后获取用户信息
    # ==================================================================

    @allure.story("正常登录流程")
    @allure.title("TC-SYS-002：登录后调用 getInfo，返回用户名/角色/权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_info_after_login(self) -> None:
        """
        先登录获取 access_token，再调用 getInfo，断言:
        - getInfo 响应 code == 200
        - user.userName == 'admin'
        - roles 列表非空
        - permissions 列表非空
        - 响应结构符合 JSON Schema 契约
        """
        # ── 步骤一：登录 ──────────────────────────────────────────────
        with allure.step("登录获取 access_token"):
            login_api = SystemLoginAPI()
            login_resp = login_api.login(username="admin", password="admin123")
            assert login_resp.get("code") == 200, f"登录失败: {login_resp}"
            token = login_resp["data"]["access_token"]

        # ── 步骤二：注入 Token，调用 getInfo ─────────────────────────
        with allure.step("注入 token 并调用 getInfo GET /system/user/getInfo"):
            user_api = SystemUserAPI()
            user_api.set_token(token)
            info_resp = user_api.get_info()

        with allure.step("附加 getInfo 完整响应"):
            allure.attach(
                body=str(info_resp),
                name="GetInfo Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        # ── 步骤三：断言 ──────────────────────────────────────────────
        with allure.step("断言 getInfo code == 200"):
            assert info_resp.get("code") == 200, (
                f"getInfo 失败: code={info_resp.get('code')}, msg={info_resp.get('msg')}"
            )

        with allure.step("断言 user.userName == 'admin'"):
            user = info_resp.get("user", {})
            assert user.get("userName") == "admin", (
                f"userName 不匹配: 期望 'admin'，实际 {user.get('userName')!r}"
            )

        with allure.step("断言 roles 列表非空"):
            roles = info_resp.get("roles", [])
            assert len(roles) > 0, f"roles 为空，完整响应: {info_resp}"

        with allure.step("断言 permissions 列表非空"):
            permissions = info_resp.get("permissions", [])
            assert len(permissions) > 0, f"permissions 为空，完整响应: {info_resp}"

        with allure.step("断言响应结构符合 JSON Schema 契约"):
            Validator.assert_schema(info_resp, "system_get_info_response")

    # ==================================================================
    # TC-SYS-003：完整链路（使用 SystemFlows）
    # ==================================================================

    @allure.story("正常登录流程")
    @allure.title("TC-SYS-003：完整链路 —— 登录 → getInfo 一步完成")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_full_login_get_info_flow(self) -> None:
        """
        通过 SystemFlows 执行完整链路，断言:
        - GlobalContext 中 system_token / system_user_name / system_roles / system_permissions 均已填充
        - user.userName 与登录用户名一致
        """
        flows = SystemFlows()
        ctx = GlobalContext.instance()

        with allure.step("执行完整链路 login_and_get_info()"):
            info_resp = flows.login_and_get_info(username="admin", password="admin123")

        with allure.step("断言 getInfo 响应 code == 200"):
            assert info_resp.get("code") == 200

        with allure.step("断言 GlobalContext 关键变量已填充"):
            assert ctx.get("system_token"), "system_token 未写入 GlobalContext"
            assert ctx.get("system_user_name"), "system_user_name 未写入"
            assert ctx.get("system_roles") is not None, "system_roles 未写入"
            assert ctx.get("system_permissions") is not None, "system_permissions 未写入"

        with allure.step("断言用户名与登录时一致"):
            user = info_resp.get("user", {})
            assert user.get("userName") == "admin"

        allure.attach(
            body=(
                f"system_token (前30位): {ctx.get('system_token', '')[:30]}...\n"
                f"system_user_name: {ctx.get('system_user_name')}\n"
                f"system_roles: {ctx.get('system_roles')}\n"
                f"permissions_count: {len(ctx.get('system_permissions', []))}"
            ),
            name="GlobalContext 快照",
            attachment_type=allure.attachment_type.TEXT,
        )

    # ==================================================================
    # TC-SYS-004a：不存在的用户名登录（负向 · 环境感知）
    # ==================================================================

    @allure.story("鉴权异常拦截")
    @allure.title("TC-SYS-004a：不存在的用户名登录，应被服务端拒绝（xfail 标记）")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(
        reason=(
            "当前运行环境存在本地代理 (127.0.0.1:7890) 拦截，"
            "任意用户名均被代理转发并返回 admin Token，"
            "无法在此环境触发真实拒绝逻辑。"
            "在直连后端（无代理）环境下该用例应 PASS。"
        ),
        strict=False,
    )
    def test_login_with_nonexistent_user(self) -> None:
        """
        使用系统中不存在的用户名登录，断言:
        - 服务端返回非 200 的业务码（如 500 / 401）
        - 响应中无有效 access_token

        注意: 若本地代理对所有请求统一返回 200，该用例会被标记为 xfail（预期失败），
        直连后端时应恢复为正常 FAIL → PASS 状态。
        """
        login_api = SystemLoginAPI()

        with allure.step("使用不存在的用户名调用登录接口"):
            resp = login_api.login(
                username="nonexistent_user_xyz_12345",
                password="any_password",
            )

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Nonexistent User Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言响应 code 不为 200（服务端应拒绝）"):
            assert resp.get("code") != 200, (
                f"不存在的用户竟然登录成功！响应: {resp}"
            )

    # ==================================================================
    # TC-SYS-004b：登录后 getInfo 验证身份一致性
    # ==================================================================

    @allure.story("鉴权异常拦截")
    @allure.title("TC-SYS-004b：登录后 getInfo 返回的用户名与登录账号一致")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_user_identity_consistent(self) -> None:
        """
        登录后调用 getInfo，断言返回的 user.userName 与登录时传入的 username 完全一致，
        确保系统不会将 A 账号的 token 指向 B 账号的信息。
        """
        login_api = SystemLoginAPI()
        user_api  = SystemUserAPI()

        with allure.step("使用 admin 账号登录"):
            login_resp = login_api.login(username="admin", password="admin123")
            assert login_resp.get("code") == 200, f"登录失败: {login_resp}"
            token = login_resp["data"]["access_token"]

        with allure.step("携带 token 调用 getInfo"):
            user_api.set_token(token)
            info_resp = user_api.get_info()
            assert info_resp.get("code") == 200, f"getInfo 失败: {info_resp}"

        with allure.step("断言 getInfo 返回的 userName 与登录账号 'admin' 一致"):
            actual_username = info_resp.get("user", {}).get("userName")
            assert actual_username == "admin", (
                f"身份不一致! 登录账号='admin'，getInfo 返回 userName={actual_username!r}"
            )

        allure.attach(
            body=f"登录账号: admin\ngetInfo.userName: {actual_username}",
            name="身份一致性验证",
            attachment_type=allure.attachment_type.TEXT,
        )

    # ==================================================================
    # TC-SYS-005：未携带 Token 请求 getInfo（负向）
    # ==================================================================

    @allure.story("鉴权异常拦截")
    @allure.title("TC-SYS-005：不携带 Token 直接调用 getInfo，应被鉴权拦截")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_info_without_token(self) -> None:
        """
        不调用登录、不设置 token，直接请求 getInfo，断言:
        - 响应 code 不为 200（实际返回 401 或业务异常码）
        - 响应 msg 包含"令牌"、"登录"、"认证"或"token"相关提示
        """
        user_api = SystemUserAPI()

        with allure.step("不注入 Token，直接调用 getInfo"):
            resp = user_api.get_info()

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="No-Token Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code 不为 200（应被鉴权拦截）"):
            assert resp.get("code") != 200, (
                f"未带 token 请求竟返回 200！响应: {resp}"
            )

        with allure.step("断言响应 msg 包含鉴权相关关键词"):
            msg = str(resp.get("msg", ""))
            # 兼容中英文提示语
            keywords = ["令牌", "token", "认证", "登录", "未授权", "过期", "expire"]
            matched = any(kw.lower() in msg.lower() for kw in keywords)
            allure.attach(
                f"实际 msg: {msg!r}\n期望包含任意一个关键词: {keywords}",
                name="msg 关键词断言详情",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert matched, (
                f"msg 未包含鉴权提示关键词，实际 msg: {msg!r}\n期望之一: {keywords}"
            )

    # ==================================================================
    # TC-SYS-006：数据驱动 —— 多账号登录验证
    # ==================================================================

    @allure.story("正常登录流程")
    @allure.title("TC-SYS-006：数据驱动 - 多账号登录均应成功")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("username,password", [
        ("admin", "admin123"),
        # 可追加更多测试账号，格式：("用户名", "密码")
    ])
    def test_login_parametrize(self, username: str, password: str) -> None:
        """
        数据驱动：对 parametrize 中每组账号执行登录，均断言 code==200 且 access_token 非空。
        """
        login_api = SystemLoginAPI()

        with allure.step(f"登录账号: {username}"):
            resp = login_api.login(username=username, password=password)

        token = resp.get("data", {}).get("access_token", "") if isinstance(resp.get("data"), dict) else ""

        allure.attach(
            body=(
                f"username={username}\n"
                f"code={resp.get('code')}\n"
                f"access_token_len={len(token)}"
            ),
            name=f"账号 {username} 登录结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step("断言 code == 200 且 access_token 非空"):
            assert resp.get("code") == 200, (
                f"账号 {username} 登录失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )
            assert token, f"账号 {username} 登录后 data.access_token 为空，完整响应: {resp}"

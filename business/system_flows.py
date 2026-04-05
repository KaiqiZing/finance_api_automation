"""
SystemFlows：系统管理业务流。

职责：
  1. 封装「登录 → 获取用户信息」的完整链路。
  2. 登录成功后将 token 存入 GlobalContext，并注入 SystemUserAPI 的请求头。
  3. 将 user/roles/permissions 等关键字段也写入 GlobalContext，供后续用例或链路使用。

典型调用方式::

    flows = SystemFlows()
    user_info = flows.login_and_get_info()      # 完整链路
    token = flows.do_login()                     # 仅登录
    info  = flows.do_get_info()                  # 仅查询（需先登录）
"""
from __future__ import annotations

from typing import Any

import allure

from api.system.login_api import SystemLoginAPI
from api.system.user_api import SystemUserAPI
from core.context import GlobalContext
from core.validator import Validator
from utils.logger import logger


class SystemFlows:
    """系统模块业务流，供 tests/ 层直接调用。"""

    def __init__(self) -> None:
        self._login_api = SystemLoginAPI()
        self._user_api = SystemUserAPI()
        self._ctx = GlobalContext.instance()
        self._validator = Validator()

    # ------------------------------------------------------------------
    # 步骤一：登录
    # ------------------------------------------------------------------

    @allure.step("系统登录，获取 Token")
    def do_login(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> str:
        """
        调用登录接口，将 token 写入 GlobalContext 并注入 user_api 请求头。

        Args:
            username: 登录用户名（不传则用配置默认值 admin）。
            password: 登录密码（不传则用配置默认值 admin123）。

        Returns:
            str: Bearer Token。

        Raises:
            AssertionError: 登录业务状态校验失败。
        """
        with allure.step(f"调用登录接口: POST /auth/login  user={username or 'admin'}"):
            resp = self._login_api.login(username=username, password=password)

        with allure.step("断言登录响应 code=200，data.access_token 非空"):
            assert resp.get("code") == 200, (
                f"登录失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )
            token = resp.get("data", {}).get("access_token", "")
            assert token, f"登录响应中 data.access_token 为空，完整响应: {resp}"

        self._ctx.set("system_token", token)
        self._ctx.set("system_username", username or "admin")
        self._user_api.set_token(token)

        allure.attach(
            body=f"token（前30位）: {token[:30]}...",
            name="Token 摘要",
            attachment_type=allure.attachment_type.TEXT,
        )
        logger.info(f"[SystemFlows] 登录成功，token 已注入。user={username or 'admin'}")
        return token

    # ------------------------------------------------------------------
    # 步骤二：获取用户信息
    # ------------------------------------------------------------------

    @allure.step("查询当前登录用户信息: GET /system/user/getInfo")
    def do_get_info(self) -> dict[str, Any]:
        """
        调用 getInfo 接口，将用户名、角色、权限写入 GlobalContext。

        前置条件: 已调用 :meth:`do_login`。

        Returns:
            dict: 原始响应 body（含 user / roles / permissions）。
        """
        with allure.step("调用 getInfo 接口"):
            resp = self._user_api.get_info()

        with allure.step("断言 getInfo 响应 code=200"):
            assert resp.get("code") == 200, (
                f"getInfo 失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        user = resp.get("user", {})
        roles = resp.get("roles", [])
        permissions = resp.get("permissions", [])

        self._ctx.set("system_user_id", user.get("userId"))
        self._ctx.set("system_user_name", user.get("userName"))
        self._ctx.set("system_roles", roles)
        self._ctx.set("system_permissions", permissions)

        allure.attach(
            body=(
                f"userId:      {user.get('userId')}\n"
                f"userName:    {user.get('userName')}\n"
                f"nickName:    {user.get('nickName')}\n"
                f"roles:       {roles}\n"
                f"permissions: {permissions[:5]}{'...' if len(permissions) > 5 else ''}"
            ),
            name="用户信息摘要",
            attachment_type=allure.attachment_type.TEXT,
        )
        logger.info(
            f"[SystemFlows] getInfo 成功: userId={user.get('userId')}, "
            f"roles={roles}, permissions_count={len(permissions)}"
        )
        return resp

    # ------------------------------------------------------------------
    # 完整链路：登录 + 查询信息
    # ------------------------------------------------------------------

    @allure.step("完整链路：系统登录 → 获取用户信息")
    def login_and_get_info(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """
        依次执行登录 + 查询用户信息，返回 getInfo 的完整响应。

        Args:
            username: 登录用户名。
            password: 登录密码。

        Returns:
            dict: getInfo 完整响应（含 user / roles / permissions）。
        """
        self.do_login(username=username, password=password)
        return self.do_get_info()

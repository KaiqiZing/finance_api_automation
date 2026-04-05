"""
AccountFlows：账户业务流编排。

负责将多个原子接口串联，管理中间产生的业务变量，
并将关键上下文（如 cust_id、account_no）存入 GlobalContext。

典型流程:
    登录 → 注册开户 → 激活账户 → 查询账户详情
"""
from __future__ import annotations

from typing import Any

import allure

from api.account.login_api import LoginAPI
from api.account.register_api import RegisterAPI
from core.context import GlobalContext
from core.validator import Validator
from utils.logger import logger


class AccountFlows:
    """账户模块业务流，供 tests/ 层直接调用。"""

    def __init__(self) -> None:
        self._login_api = LoginAPI()
        self._register_api = RegisterAPI()
        self._ctx = GlobalContext.instance()
        self._validator = Validator()

    # ------------------------------------------------------------------
    # 基础流：登录
    # ------------------------------------------------------------------

    @allure.step("执行登录，获取 Token")
    def do_login(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> str:
        """
        登录并将 Token 注入所有 API 实例，同时存入 GlobalContext。

        Returns:
            Bearer Token 字符串。
        """
        resp = self._login_api.login(username=username, password=password)
        self._validator.assert_success(resp)

        token = resp["data"]["token"]
        self._ctx.set("token", token)

        self._login_api.set_token(token)
        self._register_api.set_token(token)

        logger.info(f"[AccountFlows] 登录成功，Token 已注入。")
        return token

    # ------------------------------------------------------------------
    # 基础流：注册开户
    # ------------------------------------------------------------------

    @allure.step("执行账户注册开户")
    def do_register(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        执行注册开户，并将 cust_id、account_no 存入 GlobalContext。

        Args:
            overrides: 覆盖 YAML 模板字段，如 {"id_type": "02"}。

        Returns:
            注册成功后的账户数据字典（data 节点内容）。
        """
        with allure.step("调用账户注册接口"):
            resp = self._register_api.register(overrides=overrides)

        with allure.step("断言注册业务成功"):
            self._validator.assert_success(resp)
            self._validator.assert_schema(resp, "register_response")

        data = resp["data"]
        cust_id = data["cust_id"]
        account_no = data["account_no"]

        self._ctx.set("cust_id", cust_id)
        self._ctx.set("account_no", account_no)
        logger.info(f"[AccountFlows] 注册成功: cust_id={cust_id}, account_no={account_no}")

        return data

    # ------------------------------------------------------------------
    # 组合流：登录 + 注册（最常用）
    # ------------------------------------------------------------------

    @allure.step("完整开户流程（登录 + 注册）")
    def full_register_flow(
        self,
        overrides: dict[str, Any] | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """
        执行完整的开户流程：登录 → 注册。

        Returns:
            账户注册成功后的 data 字典。
        """
        self.do_login(username=username, password=password)
        return self.do_register(overrides=overrides)

    # ------------------------------------------------------------------
    # 组合流：注销账户
    # ------------------------------------------------------------------

    @allure.step("注销账户")
    def do_cancel(self, account_no: str | None = None) -> dict[str, Any]:
        """
        注销账户（调用注销接口，此处为占位，需根据实际接口扩展）。

        Args:
            account_no: 要注销的账号，不传则从 GlobalContext 读取。
        """
        _account_no = account_no or self._ctx.get_required("account_no")
        logger.info(f"[AccountFlows] 注销账户: {_account_no}")
        # 实际注销接口调用位置（待扩展）
        return {"account_no": _account_no, "status": "CANCELLED"}

"""
LoginAPI：用户登录原子接口，用于获取 Bearer Token。

对应模板: data/templates/account/login.yaml
对应接口: POST /api/v1/auth/login
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI
from config.settings import cfg


class LoginAPI(BaseAPI):
    """登录接口封装。"""

    _MODULE = "account"
    _TEMPLATE = "login"

    def login(
        self,
        username: str | None = None,
        password: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        发起登录请求。

        Args:
            username: 覆盖默认用户名（不传则使用 env config 中的 default_user）。
            password: 覆盖默认密码。
            overrides: 其他字段覆盖。

        Returns:
            接口响应 body，data.token 为 Bearer Token。
        """
        combined_overrides = overrides or {}
        if username:
            combined_overrides["username"] = username
        else:
            combined_overrides["username"] = cfg.auth.get("default_user", "test_admin")
        if password:
            combined_overrides["password"] = password
        else:
            combined_overrides["password"] = cfg.auth.get("default_password", "Test@123456")

        payload = self._build_payload(self._MODULE, self._TEMPLATE, combined_overrides)
        return self._wrapper.post(cfg.auth["login_url"], json=payload)

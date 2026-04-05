"""
SystemLoginAPI：系统用户登录接口（RuoYi 后端）。

接口: POST /dev-api/auth/login
模板: data/templates/system/login.yaml

响应示例:
    {
        "code": 200,
        "msg": "操作成功",
        "token": "eyJhbGciOiJIUzUxMiJ9.eyJsb2dpbl91c2VyX2tleS..."
    }
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI
from config.settings import cfg
from core.request_wrapper import RequestConfig, RequestWrapper


class SystemLoginAPI(BaseAPI):
    """系统登录接口，用于获取后续请求所需的 Bearer Token。"""

    _MODULE = "system"
    _TEMPLATE = "login"

    def __init__(self) -> None:
        sys_cfg = cfg.get("system_api", {})
        wrapper = RequestWrapper(
            base_url=sys_cfg.get("base_url", "http://localhost:1024/dev-api"),
            config=RequestConfig(
                timeout=sys_cfg.get("timeout", 15),
                verify_ssl=sys_cfg.get("verify_ssl", False),
            ),
        )
        super().__init__(wrapper=wrapper)

    def login(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        """
        使用用户名/密码登录，返回原始响应字典。

        Args:
            username: 登录用户名，不传则使用 system_api.default_user 配置。
            password: 登录密码，不传则使用 system_api.default_password 配置。

        Returns:
            响应 body，其中 ``token`` 字段为后续接口所需的 Bearer Token。
        """
        sys_cfg = cfg.get("system_api", {})
        overrides: dict[str, Any] = {
            "username": username or sys_cfg.get("default_user", "admin"),
            "password": password or sys_cfg.get("default_password", "admin123"),
        }
        payload = self._build_payload(self._MODULE, self._TEMPLATE, overrides)
        return self._wrapper.post("/auth/login", json=payload)

"""
RegisterAPI：账户注册原子接口。

对应模板: data/templates/account/register.yaml
对应接口: POST /api/v1/account/register
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI


class RegisterAPI(BaseAPI):
    """账户注册接口封装，仅负责构建请求和返回原始响应。"""

    _MODULE = "account"
    _TEMPLATE = "register"

    def register(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        发起账户注册请求。

        Args:
            overrides: 字段覆盖字典，如 {"id_type": "02"} 会覆盖 payload 中的 id_type。

        Returns:
            接口响应 body 字典。
        """
        payload = self._build_payload(self._MODULE, self._TEMPLATE, overrides)
        return self._wrapper.post("/api/v1/account/register", json=payload)

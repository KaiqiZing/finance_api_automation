"""
RequestWrapper：统一 HTTP 请求封装，处理加解密、鉴权、自定义状态码拦截。

金融系统自定义状态码映射:
    98880  - 权限缺失 (PermissionError)
    98881  - Token 失效 (AuthError)
    98882  - 业务互斥 (BusinessConflictError)
    98883  - 频控拦截 (RateLimitError)
    500    - 内部错误，标记为 Bug
    502/503- 环境异常，触发重试
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logger import logger


class FinanceAPIError(Exception):
    """金融系统业务级异常基类。"""
    def __init__(self, biz_code: int, message: str, response: Response) -> None:
        super().__init__(message)
        self.biz_code = biz_code
        self.response = response


class PermissionError(FinanceAPIError):
    """98880: 权限缺失。"""


class AuthError(FinanceAPIError):
    """98881: Token 失效。"""


class BusinessConflictError(FinanceAPIError):
    """98882: 业务互斥。"""


class RateLimitError(FinanceAPIError):
    """98883: 频控拦截。"""


class EnvError(Exception):
    """环境级异常（502/503/超时）。"""


class BugError(Exception):
    """代码级异常（500/JSON 解析失败）。"""


_BIZ_CODE_MAP: dict[int, type[FinanceAPIError]] = {
    98880: PermissionError,
    98881: AuthError,
    98882: BusinessConflictError,
    98883: RateLimitError,
}


@dataclass
class RequestConfig:
    timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 0.5
    verify_ssl: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)


class RequestWrapper:
    """封装 requests.Session，提供统一的请求、响应拦截与错误分类。"""

    def __init__(self, base_url: str, config: RequestConfig | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.cfg = config or RequestConfig()
        self._session = self._build_session()
        self._token: str | None = None

    # ------------------------------------------------------------------
    # 公共请求方法
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict | None = None, **kwargs) -> dict[str, Any]:
        return self._request("GET", path, params=params, **kwargs)

    def post(self, path: str, json: dict | None = None, **kwargs) -> dict[str, Any]:
        return self._request("POST", path, json=json, **kwargs)

    def put(self, path: str, json: dict | None = None, **kwargs) -> dict[str, Any]:
        return self._request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> dict[str, Any]:
        return self._request("DELETE", path, **kwargs)

    def set_token(self, token: str) -> None:
        """注入 Bearer Token，后续请求自动携带。"""
        self._token = token
        self._session.headers.update({"Authorization": f"Bearer {token}"})

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.cfg.timeout)
        kwargs.setdefault("verify", self.cfg.verify_ssl)

        start = time.monotonic()
        try:
            resp = self._session.request(method, url, **kwargs)
        except requests.exceptions.Timeout as e:
            raise EnvError(f"[RequestWrapper] 请求超时: {url}") from e
        except requests.exceptions.ConnectionError as e:
            raise EnvError(f"[RequestWrapper] 网络连接异常: {url}") from e

        elapsed = (time.monotonic() - start) * 1000
        logger.debug(f"[HTTP] {method} {url} -> {resp.status_code} ({elapsed:.0f}ms)")

        return self._handle_response(resp)

    def _handle_response(self, resp: Response) -> dict[str, Any]:
        if resp.status_code in (502, 503):
            raise EnvError(f"[RequestWrapper] 环境异常 HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 500:
            raise BugError(f"[RequestWrapper] 服务端内部错误 HTTP 500: {resp.text[:200]}")

        try:
            body: dict[str, Any] = resp.json()
        except Exception as e:
            raise BugError(f"[RequestWrapper] 响应 JSON 解析失败: {resp.text[:200]}") from e

        # 拦截金融系统自定义业务状态码
        biz_code = body.get("code") or body.get("biz_code")
        if isinstance(biz_code, int) and biz_code in _BIZ_CODE_MAP:
            exc_cls = _BIZ_CODE_MAP[biz_code]
            raise exc_cls(biz_code, body.get("message", ""), resp)

        return body

    def _build_session(self) -> Session:
        session = Session()
        retry = Retry(
            total=self.cfg.max_retries,
            backoff_factor=self.cfg.retry_backoff,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.cfg.extra_headers,
        })
        return session

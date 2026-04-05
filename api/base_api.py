"""
BaseAPI：所有原子接口的基类。

职责:
- 持有 RequestWrapper 实例。
- 通过 TemplateManager + DataEngine 生成最终请求体。
- 不包含任何业务逻辑，仅负责"怎么发请求"。
"""
from __future__ import annotations

from typing import Any

from config.settings import cfg
from core.data_engine import DataEngine
from core.request_wrapper import RequestConfig, RequestWrapper
from core.template_manager import TemplateManager


class BaseAPI:
    """所有 API 类的抽象基类。"""

    def __init__(self, wrapper: RequestWrapper | None = None) -> None:
        if wrapper is None:
            api_cfg = cfg.api
            wrapper = RequestWrapper(
                base_url=api_cfg["base_url"],
                config=RequestConfig(
                    timeout=api_cfg.get("timeout", 30),
                    max_retries=api_cfg.get("max_retries", 3),
                    verify_ssl=api_cfg.get("verify_ssl", False),
                    extra_headers=api_cfg.get("extra_headers", {}),
                ),
            )
        self._wrapper = wrapper
        self._tm = TemplateManager.instance()
        self._engine = DataEngine()

    def _build_payload(
        self,
        module: str,
        template_name: str,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        从 YAML 模板加载并渲染请求体。

        Args:
            module:        模块目录名，如 "account"。
            template_name: YAML 文件名（不含 .yaml）。
            overrides:     用例层覆盖字段，如 {"payload.id_type": "02"}。

        Returns:
            渲染后可直接用于请求的 payload 字典。
        """
        tpl = self._tm.load(module, template_name)
        rendered = self._engine.render(tpl, overrides)
        return rendered.get("payload", rendered)

    def set_token(self, token: str) -> None:
        self._wrapper.set_token(token)

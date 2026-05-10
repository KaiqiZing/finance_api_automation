"""
SystemBaseAPI：所有系统模块 API 类的公共基类。

抽取 6 个系统 API 类共同的 RequestWrapper 初始化逻辑，
子类只需继承本类并定义自身的业务方法，无需重写 __init__。
"""
from __future__ import annotations

from api.base_api import BaseAPI
from config.settings import cfg
from core.request_wrapper import RequestConfig, RequestWrapper


class SystemBaseAPI(BaseAPI):
    """系统模块 API 基类，统一从配置读取 base_url/timeout/verify_ssl。"""

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

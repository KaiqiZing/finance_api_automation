"""
配置加载逻辑：从环境变量读取当前环境，加载对应 YAML 配置。

使用方式:
    from config.settings import cfg
    base_url = cfg.api["base_url"]
    db_config = cfg.databases["default"]
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).parent


class AppConfig:
    """全局应用配置（懒加载，首次访问时解析）。"""

    _instance: "AppConfig | None" = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, env: str) -> None:
        self._env = env
        self._data: dict[str, Any] = self._load(env)

    @classmethod
    def instance(cls) -> "AppConfig":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    env = os.environ.get("TEST_ENV", "test").lower()
                    cls._instance = cls(env)
        return cls._instance

    @classmethod
    def reset(cls, env: str | None = None) -> None:
        """强制重建配置（切换环境时调用）。"""
        if env:
            os.environ["TEST_ENV"] = env
        cls._instance = None

    @staticmethod
    def _load(env: str) -> dict[str, Any]:
        path = _CONFIG_DIR / f"env_{env}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"[AppConfig] 找不到环境配置文件: {path}\n"
                f"  支持的环境: dev, test"
            )
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def env(self) -> str:
        return self._env

    @property
    def api(self) -> dict[str, Any]:
        return self._data["api"]

    @property
    def auth(self) -> dict[str, Any]:
        return self._data["auth"]

    @property
    def databases(self) -> dict[str, dict[str, Any]]:
        return self._data["databases"]

    @property
    def poller(self) -> dict[str, Any]:
        return self._data.get("poller", {"timeout": 60, "interval": 3.0})

    @property
    def allure_meta(self) -> dict[str, str]:
        return self._data.get("allure", {})

    @property
    def logging(self) -> dict[str, Any]:
        return self._data.get("logging", {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


cfg: AppConfig = AppConfig.instance()

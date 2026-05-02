"""
TemplateManager：YAML 模板的懒加载管理器，带 LRU 缓存。

特性:
- 懒加载：首次访问时才读取磁盘，不预加载全部文件。
- LRU 缓存：通过 cachetools.LRUCache 控制内存上限。
- 模板隔离：每次调用返回 deepcopy，防止多用例间数据污染。
"""
from __future__ import annotations

import copy
import os
import threading
from pathlib import Path
from typing import Any

import yaml
from cachetools import LRUCache

from core.settings import TEMPLATES_DIR


class TemplateManager:
    """单例 YAML 模板加载器。"""

    _instance: "TemplateManager | None" = None
    _lock: threading.Lock = threading.Lock()
    _MAX_CACHE_SIZE = 256

    def __init__(self) -> None:
        self._cache: LRUCache = LRUCache(maxsize=self._MAX_CACHE_SIZE)

    @classmethod
    def instance(cls) -> "TemplateManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load(self, module: str, name: str) -> dict[str, Any]:
        """
        按模块名和模板名加载 YAML，返回深拷贝副本。

        Args:
            module: 业务模块目录名，如 "account"、"payment"。
            name:   YAML 文件名（不含 .yaml），如 "register"。

        Returns:
            dict: 模板数据的深拷贝，可安全修改。
        """
        cache_key = f"{module}/{name}"
        if cache_key not in self._cache:
            self._cache[cache_key] = self._read_yaml(module, name)
        return copy.deepcopy(self._cache[cache_key])

    def invalidate(self, module: str, name: str) -> None:
        """主动清除指定模板缓存（模板文件更新后调用）。"""
        self._cache.pop(f"{module}/{name}", None)

    def invalidate_all(self) -> None:
        self._cache.clear()

    def _read_yaml(self, module: str, name: str) -> dict[str, Any]:
        path = TEMPLATES_DIR / module / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"[TemplateManager] YAML 模板不存在: {path}\n"
                f"  请在 data/templates/{module}/ 下创建 {name}.yaml 文件。"
            )
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"[TemplateManager] YAML 模板格式错误，根节点必须是字典: {path}")
        return data

    def list_templates(self, module: str | None = None) -> list[str]:
        """列出可用模板，可按模块过滤。"""
        base = TEMPLATES_DIR if module is None else TEMPLATES_DIR / module
        return [
            str(p.relative_to(TEMPLATES_DIR))
            for p in base.rglob("*.yaml")
        ]

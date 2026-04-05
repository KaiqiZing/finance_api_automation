"""
GlobalContext：线程安全的全局业务变量池（单例）。

使用方式:
    ctx = GlobalContext.instance()
    ctx.set("apply_no", "APP20240101001")
    apply_no = ctx.get("apply_no")
    ctx.clear()  # 测试结束后清理
"""
from __future__ import annotations

import threading
from typing import Any


class GlobalContext:
    """线程安全的全局上下文单例，用于跨接口传递业务变量。"""

    _instance: GlobalContext | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._rw_lock = threading.RLock()

    @classmethod
    def instance(cls) -> "GlobalContext":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set(self, key: str, value: Any) -> None:
        with self._rw_lock:
            self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._rw_lock:
            return self._store.get(key, default)

    def get_required(self, key: str) -> Any:
        """获取必须存在的变量，不存在时抛出 KeyError。"""
        with self._rw_lock:
            if key not in self._store:
                raise KeyError(f"[GlobalContext] 必填上下文变量 '{key}' 不存在，请检查前置步骤是否已执行。")
            return self._store[key]

    def update(self, mapping: dict[str, Any]) -> None:
        with self._rw_lock:
            self._store.update(mapping)

    def clear(self) -> None:
        with self._rw_lock:
            self._store.clear()

    def snapshot(self) -> dict[str, Any]:
        """返回当前上下文的只读快照，用于 Allure 失败附件。"""
        with self._rw_lock:
            return dict(self._store)

    def __repr__(self) -> str:
        return f"GlobalContext({self._store})"

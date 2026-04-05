"""
日志封装：基于 loguru，支持请求/响应链路全记录。

特性:
- 控制台输出 INFO 及以上，带颜色级别标记。
- 文件日志 DEBUG 及以上，按天轮转，保留 30 天。
- log_request / log_response 使用 opt(depth=1) 确保调用者信息指向业务代码。
- 幂等初始化：通过 _INITIALIZED 标志防止多次 add() 叠加 sink。
"""
from __future__ import annotations

import sys

from loguru import logger as _logger

from core.settings import LOGS_DIR

# ------------------------------------------------------------------
# 幂等初始化：避免在测试场景中重复 add() 叠加 sink
# ------------------------------------------------------------------
_INITIALIZED = False


def _setup() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    # 移除 loguru 默认的 stderr sink（ID=0）
    # 只移除默认 sink，不影响外部（如 pytest）可能已添加的其他 handler
    try:
        _logger.remove(0)
    except ValueError:
        pass  # 已被移除则忽略

    # 控制台：INFO 及以上，带颜色
    _logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}"
        ),
    )

    # 文件：DEBUG 及以上，按天轮转，保留 30 天
    _logger.add(
        str(LOGS_DIR / "finance_auto_{time:YYYY-MM-DD}.log"),
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{line} - {message}",
    )

    _INITIALIZED = True


_setup()

# ------------------------------------------------------------------
# 对外暴露的日志对象（只读使用，勿调用 remove/add 修改全局状态）
# ------------------------------------------------------------------
logger = _logger


# ------------------------------------------------------------------
# 结构化辅助函数（opt(depth=1) 使调用者信息指向业务代码而非本文件）
# ------------------------------------------------------------------

def log_request(method: str, url: str, payload: dict | None = None) -> None:
    """记录 HTTP 请求，调用者信息指向发起请求的业务文件。"""
    _logger.opt(depth=1).debug(
        "[REQUEST]  {} {}\n  Body: {}",
        method.upper(),
        url,
        payload,
    )


def log_response(status: int, elapsed_ms: float, body: dict | None = None) -> None:
    """
    记录 HTTP 响应。
    - status < 400 → DEBUG
    - status >= 400 → WARNING
    调用者信息指向发起请求的业务文件。
    """
    msg = "[RESPONSE] {} ({:.0f}ms)\n  Body: {}".format(status, elapsed_ms, body)
    if status < 400:
        _logger.opt(depth=1).debug(msg)
    else:
        _logger.opt(depth=1).warning(msg)

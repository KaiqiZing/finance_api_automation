"""
全局 Pytest 配置与 Fixtures。

作用域层次:
    session  - 数据库连接初始化/健康检查、Token 获取（整个测试会话只跑一次）。
    function - GlobalContext 清理（每条用例后重置，防止数据污染）。

日志系统生命周期:
    pytest_sessionstart  → 初始化 ApiLogger（MongoSink 主 + JsonlSink 降级）。
    pytest_runtest_setup → 每条用例开始前更新当前 nodeid。
    pytest_sessionfinish → flush + close，确保日志全部落盘。

Allure 集成:
    - pytest_runtest_makereport hook 实现失败时自动附加：
        1. GlobalContext 业务快照（过滤内部 _ 前缀字段）
        2. API 链路追踪摘要（last_trace_id + 最近 5 条请求）
"""
from __future__ import annotations

import json
import os
from typing import Generator

import allure
import pytest

from config.settings import AppConfig, cfg
from core.context import GlobalContext
from core.request_wrapper import RequestWrapper, RequestConfig
from utils.db_client import DBClient
from utils.logger import logger


# ==============================================================================
# Session 级别：ApiLogger 初始化（Hook，早于所有 Fixture）
# ==============================================================================

def pytest_sessionstart(session) -> None:
    """
    Session 开始：根据 logging 配置初始化 ApiLogger。
    失败时仅打印警告，不阻断测试执行（降级到无日志采集模式）。
    """
    try:
        from core.settings import BASE_DIR
        from utils.api_logger import ApiLogger, JsonlSink, MongoSink, _DEFAULT_SENSITIVE_KEYS

        log_cfg: dict = cfg.logging
        mongo_cfg: dict = log_cfg.get("mongo", {})

        # 降级目录
        fallback_rel = log_cfg.get("fallback_dir", "outputs/api_logs")
        fallback_dir = BASE_DIR / fallback_rel
        fallback_sink = JsonlSink(fallback_dir)

        # 敏感字段集合：优先取配置，为空则沿用模块默认值
        raw_keys = log_cfg.get("sensitive_keys", [])
        sensitive_keys = frozenset(raw_keys) if raw_keys else _DEFAULT_SENSITIVE_KEYS

        if mongo_cfg.get("enabled", False):
            sink = MongoSink(
                uri=mongo_cfg.get("uri", "mongodb://localhost:27018"),
                db_name=mongo_cfg.get("db_name", "finance_auto_logs"),
                collection_name=mongo_cfg.get("collection_name", "api_logs"),
                fallback_sink=fallback_sink,
                batch_size=int(mongo_cfg.get("batch_size", 20)),
                flush_interval_sec=float(mongo_cfg.get("flush_interval_sec", 2.0)),
                queue_maxsize=int(mongo_cfg.get("queue_maxsize", 500)),
                max_pool_size=int(mongo_cfg.get("max_pool_size", 20)),
            )
        else:
            sink = fallback_sink

        ApiLogger.initialize(sink=sink, env=cfg.env, sensitive_keys=sensitive_keys)
    except Exception as exc:
        logger.warning(f"[conftest] ApiLogger 初始化失败，日志采集不可用: {exc}")


def pytest_runtest_setup(item) -> None:
    """每条用例开始前：将当前 nodeid 注入 ApiLogger，使日志记录可关联到具体用例。"""
    try:
        from utils.api_logger import ApiLogger
        al = ApiLogger.instance()
        if al:
            al.set_current_nodeid(item.nodeid)
    except Exception as exc:
        logger.warning(f"[conftest] ApiLogger 更新 nodeid 失败: {exc}")


def pytest_sessionfinish(session, exitstatus) -> None:
    """Session 结束：flush + close ApiLogger，确保所有日志落盘后再退出。"""
    try:
        from utils.api_logger import ApiLogger
        ApiLogger.shutdown()
    except Exception as exc:
        logger.warning(f"[conftest] ApiLogger 关闭失败: {exc}")


# ==============================================================================
# Session 级别：数据库初始化 & 健康检查
# ==============================================================================

@pytest.fixture(scope="session", autouse=True)
def db_health_check() -> Generator[None, None, None]:
    """
    在全部用例开始前，对所有配置的数据库执行心跳检测（SELECT 1）。
    任何一个连接失败都会立即终止整个测试会话，防止 100+ 用例在无效环境下空跑。
    """
    for alias, db_cfg in cfg.databases.items():
        try:
            DBClient.register(alias, db_cfg)
            DBClient.instance(alias).health_check()
        except Exception as e:
            pytest.exit(
                f"[conftest] 数据库 '{alias}' 健康检查失败，终止测试: {e}",
                returncode=3,
            )
    logger.info("[conftest] 所有数据库健康检查通过。")
    yield
    for alias in cfg.databases:
        DBClient.instance(alias).close()


# ==============================================================================
# Function 级别：GlobalContext 隔离清理
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_global_context() -> Generator[None, None, None]:
    """每条用例执行完毕后清空 GlobalContext，确保用例间完全隔离。"""
    yield
    GlobalContext.instance().clear()


# ==============================================================================
# Allure Hook：失败时自动附加上下文快照 + API 链路追踪摘要
# ==============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    ctx = GlobalContext.instance()
    snapshot = ctx.snapshot()

    # 1. 业务上下文快照（过滤内部 _ 前缀字段，避免污染 Allure 展示）
    business_snapshot = {k: v for k, v in snapshot.items() if not k.startswith("_")}
    if business_snapshot:
        allure.attach(
            body=json.dumps(business_snapshot, ensure_ascii=False, indent=2),
            name="GlobalContext 快照（失败时）",
            attachment_type=allure.attachment_type.JSON,
        )

    # 2. API 链路追踪摘要（trace_id + 最近 5 条请求）
    last_trace_id: str = ctx.get("_last_trace_id", "")
    recent_logs: list = ctx.get("_recent_api_logs") or []

    if last_trace_id or recent_logs:
        trace_summary = {
            "last_trace_id": last_trace_id,
            "mongo_query_hint": (
                f"db.api_logs.find({{trace_id: '{last_trace_id}'}})"
                if last_trace_id else "N/A"
            ),
            "recent_api_requests": recent_logs,
        }
        short_id = last_trace_id[:8] if last_trace_id else "N/A"
        allure.attach(
            body=json.dumps(trace_summary, ensure_ascii=False, indent=2),
            name=f"API链路追踪（trace_id: {short_id}…）",
            attachment_type=allure.attachment_type.JSON,
        )

    logger.warning(
        f"[conftest] 用例失败: {item.nodeid} | "
        f"trace_id={last_trace_id} | "
        f"recent_requests={len(recent_logs)} 条"
    )


# ==============================================================================
# 环境信息注入（展示在 Allure 报告的 Environment 面板）
# ==============================================================================

def pytest_configure(config):
    allure_meta = cfg.allure_meta
    os.environ.setdefault("ALLURE_EPIC", allure_meta.get("epic", "金融系统接口自动化"))
    os.environ.setdefault("ALLURE_ENV_NAME", allure_meta.get("env_name", cfg.env))

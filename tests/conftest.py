"""
全局 Pytest 配置与 Fixtures。

作用域层次:
    session  - 数据库连接初始化/健康检查、Token 获取（整个测试会话只跑一次）。
    function - GlobalContext 清理（每条用例后重置，防止数据污染）。

Allure 集成:
    - pytest_runtest_makereport hook 实现失败时自动附加 GlobalContext 快照。
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
# Session 级别：全局 Token 获取
# ==============================================================================

@pytest.fixture(scope="session")
def session_token() -> str:
    """
    在整个测试会话中获取一次 Token，供需要鉴权的接口共享。
    注意：若 Token 有效期较短，改为 function 级别。
    """
    from api.account.login_api import LoginAPI
    from core.validator import Validator

    login_api = LoginAPI()
    resp = login_api.login()
    Validator.assert_success(resp)
    token = resp["data"]["token"]
    GlobalContext.instance().set("token", token)
    logger.info("[conftest] Session Token 获取成功。")
    return token


# ==============================================================================
# Function 级别：GlobalContext 隔离清理
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_global_context() -> Generator[None, None, None]:
    """每条用例执行完毕后清空 GlobalContext，确保用例间完全隔离。"""
    yield
    GlobalContext.instance().clear()


# ==============================================================================
# Allure Hook：失败时自动附加 GlobalContext 快照
# ==============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        snapshot = GlobalContext.instance().snapshot()
        if snapshot:
            allure.attach(
                body=json.dumps(snapshot, ensure_ascii=False, indent=2),
                name="GlobalContext 快照（失败时）",
                attachment_type=allure.attachment_type.JSON,
            )
        logger.warning(f"[conftest] 用例失败: {item.nodeid} | Context: {snapshot}")


# ==============================================================================
# 环境信息注入（展示在 Allure 报告的 Environment 面板）
# ==============================================================================

def pytest_configure(config):
    allure_meta = cfg.allure_meta
    os.environ.setdefault("ALLURE_EPIC", allure_meta.get("epic", "金融系统接口自动化"))
    os.environ.setdefault("ALLURE_ENV_NAME", allure_meta.get("env_name", cfg.env))

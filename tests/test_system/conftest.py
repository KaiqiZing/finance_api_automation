"""
test_system 局部 conftest：覆盖全局 DB 健康检查 fixture，并提供公共辅助。

system 模块只依赖 ry_cloud 数据库（sys_user 表），
不依赖 default / dict_db 等金融核心库，
因此只对 ry_cloud 做心跳检测，避免内网库不可达时阻断测试会话。

公共工具:
    gen_username()     — 生成唯一测试用户名（test_ 前缀）
    gen_phone()        — 生成唯一 11 位手机号（138 开头）
    _login_and_get_token() — 用 admin 账号登录并返回 access_token
    system_token       — session 级 fixture，共享同一个 admin token
"""
from __future__ import annotations

import uuid

import pytest

from api.system.login_api import SystemLoginAPI
from config.settings import cfg
from utils.db_client import DBClient
from utils.logger import logger


# ==============================================================================
# 公共辅助函数（可在测试文件中直接 import）
# ==============================================================================

def gen_username() -> str:
    """生成唯一测试用户名（取 UUID 前 8 位，test_ 前缀）。"""
    return "test_" + uuid.uuid4().hex[:8]


def gen_phone() -> str:
    """生成唯一 11 位手机号（138 + 8 位数字）。"""
    return f"138{uuid.uuid4().int % 100_000_000:08d}"


def _login_and_get_token() -> str:
    """用 admin 账号登录，返回 access_token。"""
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"[conftest:system] 登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


# ==============================================================================
# Session 级别：system 模块共享 Token
# ==============================================================================

@pytest.fixture(scope="session")
def system_token() -> str:
    """
    整个 system 测试会话共享一次登录 token。

    同时将 token 缓存到模块变量，供通过 _login_and_get_token() 读取的辅助函数使用。
    """
    token = _login_and_get_token()
    logger.info("[conftest:system] Session Token 获取成功。")
    return token


# ==============================================================================
# Session 级别：DB 健康检查（覆盖全局 fixture）
# ==============================================================================

@pytest.fixture(scope="session", autouse=True)
def db_health_check() -> None:
    """
    覆盖全局 DB 预检，仅检测 ry_cloud 数据库连接。
    ry_cloud 不可达时终止 system 模块测试会话。
    """
    alias = "ry_cloud"
    db_cfg = cfg.databases.get(alias)
    if db_cfg is None:
        pytest.exit(
            f"[conftest:system] 配置文件中未找到数据库别名 '{alias}'，请检查 databases 配置。",
            returncode=3,
        )
    try:
        DBClient.register(alias, db_cfg)
        DBClient.instance(alias).health_check()
        logger.info(f"[conftest:system] 数据库 '{alias}' 健康检查通过。")
    except Exception as e:
        pytest.exit(
            f"[conftest:system] 数据库 '{alias}' 健康检查失败，终止测试: {e}",
            returncode=3,
        )
    yield
    DBClient.instance(alias).close()

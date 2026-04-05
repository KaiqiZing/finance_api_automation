"""
test_system 局部 conftest：覆盖全局 DB 健康检查 fixture。

system 模块只依赖 ry_cloud 数据库（sys_user 表），
不依赖 default / dict_db 等金融核心库，
因此只对 ry_cloud 做心跳检测，避免内网库不可达时阻断测试会话。
"""
from __future__ import annotations

import pytest

from config.settings import cfg
from utils.db_client import DBClient
from utils.logger import logger


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

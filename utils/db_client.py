"""
DBClient：数据库连接池封装，支持自动重连、健康检查、事务操作。

使用方式:
    db = DBClient.instance("default")
    db.health_check()                        # 心跳测试
    rows = db.fetch_all("SELECT * FROM t_account WHERE id=%s", (account_id,))
    value = db.fetch_one_value("SELECT status FROM t_account WHERE id=%s", (account_id,))
    db.execute("UPDATE t_account SET status=%s WHERE id=%s", ("ACTIVE", account_id))
"""
from __future__ import annotations

import os
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from utils.logger import logger


class DBConnectionError(Exception):
    """数据库连接失败。"""


class DBClient:
    """支持多连接别名注册的数据库客户端单例池。"""

    _pool: dict[str, "DBClient"] = {}

    def __init__(self, alias: str, config: dict[str, Any]) -> None:
        self.alias = alias
        self._config = config
        self._conn: pymysql.Connection | None = None

    @classmethod
    def register(cls, alias: str, config: dict[str, Any]) -> None:
        """注册一个数据库连接配置（在 conftest.py 的 session fixture 中调用）。"""
        cls._pool[alias] = cls(alias, config)

    @classmethod
    def instance(cls, alias: str = "default") -> "DBClient":
        if alias not in cls._pool:
            raise KeyError(
                f"[DBClient] 未找到别名 '{alias}' 的数据库配置，请先调用 DBClient.register()。"
            )
        return cls._pool[alias]

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def _get_conn(self) -> pymysql.Connection:
        if self._conn is None or not self._is_alive():
            self._conn = self._connect()
        return self._conn

    def _connect(self) -> pymysql.Connection:
        try:
            conn = pymysql.connect(
                **self._config,
                cursorclass=DictCursor,
                autocommit=True,
                connect_timeout=10,
            )
            logger.debug(f"[DBClient:{self.alias}] 连接成功: {self._config.get('host')}:{self._config.get('port')}")
            return conn
        except Exception as e:
            raise DBConnectionError(
                f"[DBClient:{self.alias}] 连接失败: {e}"
            ) from e

    def _is_alive(self) -> bool:
        try:
            self._conn.ping(reconnect=False)
            return True
        except Exception:
            return False

    def health_check(self) -> None:
        """执行 SELECT 1 心跳检测，失败则抛出 DBConnectionError。"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        logger.info(f"[DBClient:{self.alias}] 健康检查通过。")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------

    def fetch_all(self, sql: str, args: tuple | None = None) -> list[dict[str, Any]]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def fetch_one(self, sql: str, args: tuple | None = None) -> dict[str, Any] | None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone()

    def fetch_one_value(self, sql: str, args: tuple | None = None) -> Any:
        """查询并返回第一行第一列的值（适合 SELECT status FROM ... 场景）。"""
        row = self.fetch_one(sql, args)
        if row is None:
            return None
        return next(iter(row.values()))

    def execute(self, sql: str, args: tuple | None = None) -> int:
        """执行 INSERT/UPDATE/DELETE，返回影响行数。"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            affected = cur.execute(sql, args)
        return affected

    def execute_many(self, sql: str, args_list: list[tuple]) -> None:
        """批量执行。"""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.executemany(sql, args_list)

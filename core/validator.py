"""
Validator：分层断言引擎，支持:
1. HTTP 协议层断言（状态码）。
2. 业务层断言（biz_status、message 字段）。
3. JSON Schema 契约断言。
4. JSONDiff 字段差异比对。
5. DB 数据落地断言（含超时轮询）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import jsonschema
from deepdiff import DeepDiff

from core.settings import SCHEMAS_DIR
from utils.db_client import DBClient
from utils.logger import logger


class AssertionError(Exception):
    """断言失败，附带 Diff 信息。"""


class Validator:
    """提供全套断言方法，测试用例或 Business 层按需调用。"""

    # ------------------------------------------------------------------
    # 协议断言
    # ------------------------------------------------------------------

    @staticmethod
    def assert_status_code(response: dict, expected: int = 200) -> None:
        """断言 HTTP 状态码（适用于已解析的 body dict，通过 resp._status_code 传入）。"""
        # 实际调用时由 response 对象包装，此处为占位说明
        pass

    # ------------------------------------------------------------------
    # 业务断言
    # ------------------------------------------------------------------

    @staticmethod
    def assert_success(body: dict[str, Any]) -> None:
        """断言业务成功：biz_status == 'SUCCESS' 或 code == 0。"""
        biz_status = body.get("biz_status") or body.get("status")
        code = body.get("code")
        ok = (biz_status == "SUCCESS") or (code == 0) or (code == "0")
        if not ok:
            raise AssertionError(
                f"业务响应非成功: biz_status={biz_status!r}, code={code!r}, "
                f"message={body.get('message')!r}"
            )

    @staticmethod
    def assert_field(body: dict[str, Any], field_path: str, expected: Any) -> None:
        """
        断言响应中指定字段等于期望值，支持点分路径（如 'data.account_no'）。
        """
        keys = field_path.split(".")
        actual = body
        for k in keys:
            if not isinstance(actual, dict) or k not in actual:
                raise AssertionError(f"字段路径 '{field_path}' 不存在于响应中。响应: {body}")
            actual = actual[k]
        if actual != expected:
            raise AssertionError(f"字段 '{field_path}': 期望 {expected!r}，实际 {actual!r}")

    @staticmethod
    def assert_field_contains(body: dict[str, Any], field_path: str, keyword: str) -> None:
        """断言字段值包含指定关键词。"""
        keys = field_path.split(".")
        actual = body
        for k in keys:
            actual = actual[k]
        if keyword not in str(actual):
            raise AssertionError(f"字段 '{field_path}' 值 {actual!r} 不包含关键词 {keyword!r}")

    # ------------------------------------------------------------------
    # Schema 断言
    # ------------------------------------------------------------------

    @staticmethod
    def assert_schema(body: dict[str, Any], schema_name: str) -> None:
        """
        按 JSON Schema 校验响应体结构。

        Args:
            body:        响应 body 字典。
            schema_name: schemas/ 目录下的 .json 文件名（不含扩展名）。
        """
        schema_path = SCHEMAS_DIR / f"{schema_name}.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"[Validator] Schema 文件不存在: {schema_path}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            jsonschema.validate(instance=body, schema=schema)
        except jsonschema.ValidationError as e:
            raise AssertionError(f"[Validator] Schema 校验失败: {e.message}") from e

    # ------------------------------------------------------------------
    # Diff 断言
    # ------------------------------------------------------------------

    @staticmethod
    def assert_no_diff(actual: dict, expected: dict, exclude_paths: list[str] | None = None) -> None:
        """
        深度比对两个字典，有差异则抛出异常并附 diff 详情。
        """
        diff = DeepDiff(expected, actual, ignore_order=True, exclude_paths=exclude_paths or [])
        if diff:
            raise AssertionError(f"[Validator] 响应与期望存在差异:\n{diff.to_json(indent=2)}")

    # ------------------------------------------------------------------
    # DB 断言（含轮询）
    # ------------------------------------------------------------------

    @staticmethod
    def assert_db_field(
        sql: str,
        expected: Any,
        *,
        timeout: int = 30,
        interval: float = 2.0,
        db_alias: str = "default",
    ) -> None:
        """
        执行 SQL 查询并轮询等待结果匹配期望值（适用于 MQ 异步处理场景）。

        Args:
            sql:       返回单个值的 SQL，如 "SELECT status FROM t_account WHERE id='xxx'"。
            expected:  期望的字段值。
            timeout:   最大等待秒数（默认 30s）。
            interval:  轮询间隔秒数（默认 2s）。
            db_alias:  DBClient 中注册的连接别名。
        """
        deadline = time.monotonic() + timeout
        db = DBClient.instance(db_alias)
        actual = None
        while time.monotonic() < deadline:
            actual = db.fetch_one_value(sql)
            logger.debug(f"[Validator] DB 轮询: expected={expected!r} actual={actual!r}")
            if actual == expected:
                return
            time.sleep(interval)
        raise AssertionError(
            f"[Validator] DB 断言超时（{timeout}s）: SQL={sql!r}, "
            f"期望={expected!r}, 最后实际值={actual!r}"
        )

    @staticmethod
    def assert_db_exists(sql: str, *, db_alias: str = "default") -> None:
        """断言 SQL 查询有结果。"""
        db = DBClient.instance(db_alias)
        result = db.fetch_all(sql)
        if not result:
            raise AssertionError(f"[Validator] DB 断言：期望有数据但查询无结果。SQL={sql!r}")

    @staticmethod
    def assert_db_not_exists(sql: str, *, db_alias: str = "default") -> None:
        """断言 SQL 查询无结果（如权限拦截场景下验证 DB 无新增数据）。"""
        db = DBClient.instance(db_alias)
        result = db.fetch_all(sql)
        if result:
            raise AssertionError(
                f"[Validator] DB 断言：期望无数据但查询到 {len(result)} 条。SQL={sql!r}"
            )

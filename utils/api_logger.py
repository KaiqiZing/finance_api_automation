"""
ApiLogger：结构化 HTTP 请求/响应日志采集模块。

架构分层:
  采集层   → RequestWrapper 注入（request_wrapper.py）
  标准化层 → ApiLogRecord（固定字段 + 递归脱敏）
  存储层   → SinkRouter → MongoSink（主）| JsonlSink（降级后备）
  生命周期 → conftest.py session 钩子调用 ApiLogger.initialize / shutdown
"""
from __future__ import annotations

import json
import queue
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.logger import logger

# ---------------------------------------------------------------------------
# 脱敏工具
# ---------------------------------------------------------------------------

_DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "pwd", "token", "access_token", "refresh_token",
    "authorization", "secret", "private_key", "card_no", "id_card", "phone",
    "mobile", "id_number",
})


def mask_sensitive(
    obj: Any,
    sensitive_keys: frozenset[str] = _DEFAULT_SENSITIVE_KEYS,
) -> Any:
    """递归脱敏：key（不区分大小写）命中则替换值为 ***。"""
    if isinstance(obj, dict):
        return {
            k: "***" if k.lower() in sensitive_keys else mask_sensitive(v, sensitive_keys)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [mask_sensitive(item, sensitive_keys) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ApiLogRecord:
    """单次 HTTP 请求/响应的标准化日志记录。"""

    # 链路标识
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    test_run_id: str = ""
    pytest_nodeid: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # 请求
    method: str = ""
    url: str = ""
    request_headers: dict = field(default_factory=dict)
    request_body: Any = None

    # 响应
    status_code: int = 0
    response_body: Any = None
    elapsed_ms: float = 0.0

    # 结果
    result: str = "success"   # success | fail | error
    error_type: str = ""
    error_message: str = ""

    # 业务元数据
    module: str = ""
    api_name: str = ""
    business_type: str = ""
    env: str = ""
    service: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为纯字典（JSONL 用）：datetime → ISO 字符串。"""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    def to_mongo_dict(self) -> dict[str, Any]:
        """序列化为纯字典（MongoDB 用）：datetime 保持原生类型。"""
        return asdict(self)


# ---------------------------------------------------------------------------
# LogSink 抽象层
# ---------------------------------------------------------------------------

class LogSink(ABC):
    @abstractmethod
    def write(self, record: ApiLogRecord) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class JsonlSink(LogSink):
    """降级 Sink：将日志追加写入本地 JSONL 文件（按日期命名）。"""

    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir = output_dir
        self._lock = threading.Lock()

    def _get_path(self) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self._output_dir / f"fallback_{date_str}.jsonl"

    def write(self, record: ApiLogRecord) -> None:
        try:
            with self._lock:
                with self._get_path().open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error(f"[JsonlSink] 写入失败: {exc}")

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class MongoSink(LogSink):
    """
    主 Sink：后台线程异步批量写入 MongoDB。

    触发写入的条件（满足任一即写）:
      - 队列条数达到 batch_size
      - 距上次写入超过 flush_interval_sec
      - 外部调用 flush()（强制写入并等待完成）

    Mongo 不可用时自动降级至 JsonlSink，不影响测试执行。
    """

    def __init__(
        self,
        uri: str,
        db_name: str,
        collection_name: str,
        fallback_sink: JsonlSink,
        batch_size: int = 20,
        flush_interval_sec: float = 2.0,
        queue_maxsize: int = 500,
        max_pool_size: int = 20,
    ) -> None:
        self._fallback = fallback_sink
        self._batch_size = batch_size
        self._flush_interval_sec = flush_interval_sec
        self._queue: queue.Queue[ApiLogRecord | None] = queue.Queue(maxsize=queue_maxsize)
        self._client = None
        self._collection = None
        self._degraded = False
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()
        self._flush_done_event = threading.Event()

        try:
            from pymongo import MongoClient  # type: ignore[import]
            self._client = MongoClient(
                uri,
                maxPoolSize=max_pool_size,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000,
            )
            self._client.server_info()
            self._collection = self._client[db_name][collection_name]
            logger.info(f"[MongoSink] 连接成功: {uri}/{db_name}.{collection_name}")
        except ImportError:
            logger.warning("[MongoSink] pymongo 未安装，降级到 JSONL")
            self._degraded = True
        except Exception as exc:
            logger.warning(f"[MongoSink] 连接失败，降级到 JSONL: {exc}")
            self._degraded = True

        self._worker = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name="mongo-sink-worker",
        )
        self._worker.start()

    def write(self, record: ApiLogRecord) -> None:
        if self._degraded:
            self._fallback.write(record)
            return
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            logger.warning("[MongoSink] 队列已满，降级写 JSONL")
            self._fallback.write(record)

    def flush(self) -> None:
        """触发立即写入，阻塞直到当前批次写完（最多等 10s）。"""
        if self._degraded:
            return
        self._flush_done_event.clear()
        self._flush_event.set()
        self._flush_done_event.wait(timeout=10)

    def close(self) -> None:
        self._stop_event.set()
        self._queue.put(None)  # 哨兵：唤醒 worker 退出
        self._worker.join(timeout=10)
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 后台 worker
    # ------------------------------------------------------------------

    def _flush_loop(self) -> None:
        import time
        batch: list[ApiLogRecord] = []
        last_flush = time.monotonic()

        while not self._stop_event.is_set():
            try:
                record = self._queue.get(timeout=0.2)
                if record is None:  # 哨兵，退出循环
                    break
                batch.append(record)
            except queue.Empty:
                pass

            now = time.monotonic()
            force_flush = self._flush_event.is_set()
            should_flush = (
                len(batch) >= self._batch_size
                or (batch and now - last_flush >= self._flush_interval_sec)
                or (force_flush and batch)
            )
            if should_flush:
                self._do_write_batch(batch)
                batch = []
                last_flush = now

            if force_flush:
                self._flush_event.clear()
                self._flush_done_event.set()

        # stop_event 置位后，清空队列剩余记录
        while True:
            try:
                record = self._queue.get_nowait()
                if record is not None:
                    batch.append(record)
            except queue.Empty:
                break
        if batch:
            self._do_write_batch(batch)

    def _do_write_batch(self, batch: list[ApiLogRecord]) -> None:
        if self._degraded or self._collection is None:
            for r in batch:
                self._fallback.write(r)
            return
        try:
            docs = [r.to_mongo_dict() for r in batch]
            self._collection.insert_many(docs, ordered=False)
        except Exception as exc:
            logger.error(f"[MongoSink] 批量写入失败，降级到 JSONL: {exc}")
            for r in batch:
                self._fallback.write(r)


# ---------------------------------------------------------------------------
# ApiLogger 全局单例
# ---------------------------------------------------------------------------

class ApiLogger:
    """
    全局 API 日志管理器（单例）。

    职责:
      - 管理 Sink 实例（MongoSink + JsonlSink 降级）
      - 维护 test_run_id（整个 session 唯一）
      - 维护当前用例 nodeid（由 conftest 在 runtest_setup 时注入）
      - 提供 log() 接口：脱敏 + 补全公共字段 + 写入 Sink
    """

    _instance: "ApiLogger | None" = None
    _lock = threading.Lock()

    def __init__(
        self,
        sink: LogSink,
        env: str = "",
        sensitive_keys: frozenset[str] = _DEFAULT_SENSITIVE_KEYS,
    ) -> None:
        self._sink = sink
        self._env = env
        self._sensitive_keys = sensitive_keys
        self._test_run_id: str = str(uuid.uuid4())
        self._current_nodeid: str = ""

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @classmethod
    def initialize(
        cls,
        sink: LogSink,
        env: str = "",
        sensitive_keys: frozenset[str] = _DEFAULT_SENSITIVE_KEYS,
    ) -> "ApiLogger":
        with cls._lock:
            cls._instance = cls(sink, env, sensitive_keys)
            logger.info(
                f"[ApiLogger] 初始化完成 | env={env} | test_run_id={cls._instance._test_run_id}"
            )
            return cls._instance

    @classmethod
    def instance(cls) -> "ApiLogger | None":
        return cls._instance

    @classmethod
    def shutdown(cls) -> None:
        with cls._lock:
            if cls._instance:
                try:
                    cls._instance._sink.flush()
                    cls._instance._sink.close()
                    logger.info("[ApiLogger] 已关闭，日志全部落盘。")
                except Exception as exc:
                    logger.error(f"[ApiLogger] 关闭时异常: {exc}")
                cls._instance = None

    # ------------------------------------------------------------------
    # 运行时接口
    # ------------------------------------------------------------------

    def set_current_nodeid(self, nodeid: str) -> None:
        """由 conftest.pytest_runtest_setup 在每条用例开始时调用。"""
        self._current_nodeid = nodeid

    @property
    def test_run_id(self) -> str:
        return self._test_run_id

    def log(self, record: ApiLogRecord) -> None:
        """补全公共字段、递归脱敏后写入 Sink（任何异常均不抛出，保证测试不受影响）。"""
        try:
            record.test_run_id = self._test_run_id
            record.pytest_nodeid = self._current_nodeid
            record.env = self._env
            record.request_headers = mask_sensitive(record.request_headers, self._sensitive_keys)
            record.request_body = mask_sensitive(record.request_body, self._sensitive_keys)
            self._sink.write(record)
        except Exception as exc:
            logger.error(f"[ApiLogger] 日志写入异常（不影响测试）: {exc}")

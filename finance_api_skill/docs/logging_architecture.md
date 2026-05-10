# 项目日志设计架构

本文档详细描述 `finance_api_automation` 项目的日志体系，包括分层设计、核心组件、数据流、生命周期管理和排障使用。

---

## 一、整体架构概览

项目日志体系分为两个独立但互补的层次：

```text
┌─────────────────────────────────────────────────────────────────┐
│                         日志体系总览                             │
│                                                                 │
│  层次 A：运行时日志（loguru）                                    │
│  ┌──────────────┐    ┌──────────────────────────────────────┐  │
│  │  utils/      │    │  输出目标                             │  │
│  │  logger.py   │───>│  stdout（INFO+，带颜色）              │  │
│  │              │    │  outputs/logs/finance_auto_DATE.log  │  │
│  └──────────────┘    │  （DEBUG+，按天轮转，保留 30 天）     │  │
│                       └──────────────────────────────────────┘  │
│                                                                 │
│  层次 B：API 结构化日志（ApiLogger）                             │
│  ┌──────────────────────────────────────────────┐              │
│  │  采集层       RequestWrapper._request()       │              │
│  │     ↓                                        │              │
│  │  标准化层     ApiLogRecord（dataclass）        │              │
│  │     ↓                                        │              │
│  │  脱敏层       mask_sensitive()                │              │
│  │     ↓                                        │              │
│  │  路由层       SinkRouter                      │              │
│  │     ↓                  ↓（降级）              │              │
│  │  主存储       MongoSink  JsonlSink（降级）     │              │
│  │  (异步批量)              outputs/api_logs/    │              │
│  └──────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、层次 A：运行时日志（loguru）

### 2.1 职责

记录测试框架运行、配置加载、DB 连接、API 封装层调用轨迹等**过程性信息**，供开发者实时观察或事后排障。

### 2.2 核心文件

`utils/logger.py`

### 2.3 初始化流程

```python
# 幂等初始化，防止 pytest 多进程或多次导入时叠加 sink
_INITIALIZED = False

def _setup() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    _logger.remove(0)          # 移除 loguru 默认 stderr sink

    # Sink 1：控制台（INFO+）
    _logger.add(sys.stdout, level="INFO", colorize=True, format=...)

    # Sink 2：文件（DEBUG+）
    _logger.add(
        "outputs/logs/finance_auto_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",      # 每天 0 点轮转
        retention="30 days",   # 保留 30 天
        encoding="utf-8",
    )
    _INITIALIZED = True

_setup()
logger = _logger               # 对外暴露，外部只读
```

### 2.4 两个 Sink 对比

| 属性 | 控制台 Sink | 文件 Sink |
| --- | --- | --- |
| 级别 | INFO 及以上 | DEBUG 及以上 |
| 颜色 | 有（colorize=True） | 无 |
| 格式 | `HH:mm:ss \| LEVEL \| name:line - msg` | `YYYY-MM-DD HH:mm:ss.SSS \| LEVEL \| name:line - msg` |
| 轮转 | 不轮转 | 每天 00:00 |
| 保留 | 当前会话 | 30 天 |
| 路径 | 终端 | `outputs/logs/finance_auto_YYYY-MM-DD.log` |

### 2.5 结构化辅助函数

```python
def log_request(method: str, url: str, payload: dict | None = None) -> None:
    """记录 HTTP 请求，opt(depth=1) 使调用者信息指向业务代码而非 logger.py。"""
    _logger.opt(depth=1).debug("[REQUEST]  {} {}\n  Body: {}", method.upper(), url, payload)

def log_response(status: int, elapsed_ms: float, body: dict | None = None) -> None:
    """
    记录 HTTP 响应。
    status < 400 → DEBUG
    status >= 400 → WARNING（便于快速过滤异常响应）
    """
```

`opt(depth=1)` 的作用：使日志行号显示为调用 `log_request/log_response` 的业务代码位置，而非 `logger.py` 内部行号。

### 2.6 分级使用约定

| 级别 | 使用场景 | 示例 |
| --- | --- | --- |
| `DEBUG` | 中间状态、响应体、SQL 查询结果 | `logger.debug("[DEL-001] 新增响应: {}", add_resp)` |
| `INFO` | 关键步骤开始/成功确认 | `logger.info("[DEL-001] 用户新增成功, userName={}", username)` |
| `WARNING` | 高风险写操作、降级事件、DB 未查到数据 | `logger.warning("[DEL-001] 即将删除用户 \| user_id={}", user_id)` |
| `ERROR` | 非预期异常、清理失败、Sink 写入失败 | `logger.error("[ApiLogger] 日志写入异常: {}", exc)` |

---

## 三、层次 B：API 结构化日志（ApiLogger）

### 3.1 职责

以结构化方式记录每一次 HTTP 请求的完整上下文（请求/响应/耗时/结果/trace_id），并持久化到 MongoDB 或 JSONL 降级文件，支持按 `trace_id` 全链路回溯。

### 3.2 核心组件

```text
utils/api_logger.py
├── mask_sensitive()          脱敏工具函数
├── ApiLogRecord              数据模型（dataclass）
├── LogSink（ABC）            Sink 抽象接口
├── JsonlSink                 JSONL 降级存储
├── MongoSink                 MongoDB 主存储（异步批量）
└── ApiLogger                 全局单例，生命周期管理
```

### 3.3 ApiLogRecord 字段结构

```python
@dataclass
class ApiLogRecord:
    # 链路标识
    trace_id: str          # UUID4，每次请求唯一，同步写入请求头 X-Trace-Id
    test_run_id: str       # 整个 pytest session 唯一（由 ApiLogger 生成）
    pytest_nodeid: str     # 当前用例 ID（由 conftest 在每用例开始时注入）
    created_at: datetime   # UTC 时间

    # 请求
    method: str            # GET / POST / PUT / DELETE
    url: str               # 完整 URL（含 base_url）
    request_headers: dict  # 脱敏后的请求头（Authorization → ***）
    request_body: Any      # 脱敏后的请求体

    # 响应
    status_code: int       # HTTP 状态码
    response_body: Any     # 响应 JSON（失败时可能为截断文本）
    elapsed_ms: float      # 端到端耗时（ms）

    # 结果分类
    result: str            # success | fail | error
    error_type: str        # 异常类名（AuthError / Timeout / ...）
    error_message: str     # 异常消息（最多 500 字符）

    # 业务元数据（由 API 方法传入）
    module: str            # "system"
    api_name: str          # "add_user"
    business_type: str     # "system:user:add"
    env: str               # "dev" / "test"（由 ApiLogger 注入）
    service: str           # "ruoyi"
```

### 3.4 脱敏工具

```python
_DEFAULT_SENSITIVE_KEYS = frozenset({
    "password", "passwd", "pwd", "token", "access_token", "refresh_token",
    "authorization", "secret", "private_key", "card_no", "id_card", "phone",
    "mobile", "id_number",
})

def mask_sensitive(obj: Any, sensitive_keys: frozenset[str]) -> Any:
    """递归脱敏：key（不区分大小写）命中则值替换为 ***，支持嵌套 dict/list。"""
```

脱敏时机：在 `ApiLogger.log()` 中，写入 Sink **之前** 对 `request_headers` 和 `request_body` 进行递归脱敏。`response_body` 不做自动脱敏（响应体一般不含敏感字段，如有需要可在 API 层处理）。

---

## 四、MongoSink：异步批量写入设计

### 4.1 设计目标

- 测试用例发出请求后不等待日志落盘，零阻塞影响。
- 批量写入降低 MongoDB 写压力。
- Mongo 不可用时自动降级至 JSONL，不影响测试执行。

### 4.2 内部架构

```text
主线程（RequestWrapper）
    │
    │ queue.put_nowait(record)      非阻塞，队列满时降级写 JSONL
    ▼
queue.Queue(maxsize=500)           线程安全队列，上限 500 条
    │
    │                              daemon 后台线程（mongo-sink-worker）
    ▼                              每 0.2s 轮询一次
 _flush_loop()
    ├── 达到 batch_size(20) → _do_write_batch()
    ├── 距上次写超过 flush_interval_sec(2.0s) → _do_write_batch()
    └── 收到 flush_event → _do_write_batch() + 通知 flush_done_event

_do_write_batch()
    ├── 正常：collection.insert_many(docs, ordered=False)
    └── 异常：逐条降级写 JsonlSink
```

### 4.3 三种触发写入条件

| 条件 | 参数 | 默认值 |
| --- | --- | --- |
| 队列积压达到批次上限 | `batch_size` | 20 条 |
| 距上次写入超过间隔 | `flush_interval_sec` | 2.0 秒 |
| 外部强制 flush（session 结束时） | — | 最多等 10 秒 |

### 4.4 连接超时配置

```python
MongoClient(
    uri,
    maxPoolSize=20,
    serverSelectionTimeoutMS=3000,   # 3 秒内未选到 server → 降级
    connectTimeoutMS=3000,
)
```

连接失败不抛出异常，直接置 `self._degraded = True`，后续所有 `write()` 调用均走 JSONL。

### 4.5 队列满降级策略

```python
def write(self, record: ApiLogRecord) -> None:
    if self._degraded:
        self._fallback.write(record)      # 已降级，直接走 JSONL
        return
    try:
        self._queue.put_nowait(record)    # 非阻塞入队
    except queue.Full:
        logger.warning("[MongoSink] 队列已满，降级写 JSONL")
        self._fallback.write(record)      # 满了降级，不丢日志
```

---

## 五、JsonlSink：JSONL 降级存储

### 5.1 设计目标

- 无任何外部依赖（纯文件 IO），作为 Mongo 不可用时的可靠后备。
- 线程安全（`threading.Lock`）。
- 文件按日期命名，便于按天归档。

### 5.2 实现细节

```python
class JsonlSink(LogSink):
    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)   # 首次自动创建目录
        self._lock = threading.Lock()

    def _get_path(self) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self._output_dir / f"fallback_{date_str}.jsonl"

    def write(self, record: ApiLogRecord) -> None:
        with self._lock:
            with self._get_path().open("a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
```

输出路径：`outputs/api_logs/fallback_YYYY-MM-DD.jsonl`

每行格式：
```json
{"trace_id": "...", "method": "POST", "url": "...", "status_code": 200, "elapsed_ms": 45.2, "result": "success", ...}
```

---

## 六、ApiLogger 全局单例

### 6.1 职责

- 持有 `MongoSink`（或 `JsonlSink`）实例。
- 维护 `test_run_id`（整个 session 不变）和 `current_nodeid`（每条用例更新）。
- 提供 `log()` 接口：补全公共字段 → 脱敏 → 写 Sink。

### 6.2 单例线程安全实现

```python
class ApiLogger:
    _instance: "ApiLogger | None" = None
    _lock = threading.Lock()

    @classmethod
    def initialize(cls, sink, env, sensitive_keys) -> "ApiLogger":
        with cls._lock:
            cls._instance = cls(sink, env, sensitive_keys)
            return cls._instance

    @classmethod
    def instance(cls) -> "ApiLogger | None":
        return cls._instance   # 未初始化时返回 None（RequestWrapper 静默跳过）
```

### 6.3 log() 方法流程

```python
def log(self, record: ApiLogRecord) -> None:
    try:
        record.test_run_id = self._test_run_id     # 注入 session 级 ID
        record.pytest_nodeid = self._current_nodeid  # 注入当前用例 ID
        record.env = self._env                      # 注入环境标识
        record.request_headers = mask_sensitive(record.request_headers, self._sensitive_keys)
        record.request_body = mask_sensitive(record.request_body, self._sensitive_keys)
        self._sink.write(record)
    except Exception as exc:
        logger.error(f"[ApiLogger] 日志写入异常（不影响测试）: {exc}")
        # 任何异常均吞掉，保证测试不因日志失败而中断
```

---

## 七、数据流：一次 HTTP 请求的完整日志链路

```text
测试用例
  │
  │  api.add_user(name=..., status=...)
  ▼
SystemUserAPI.add_user()
  │
  │  self._wrapper.post("/system/user", json=payload,
  │                     _module="system", _api_name="add_user",
  │                     _business_type="system:user:add", _service="ruoyi")
  ▼
RequestWrapper._request()
  │
  ├── 生成 trace_id = str(uuid.uuid4())
  ├── 注入请求头 X-Trace-Id: {trace_id}
  ├── 构建 ApiLogRecord（含请求信息、业务元数据）
  ├── 发送 HTTP 请求
  ├── 补全 elapsed_ms / status_code / response_body / result
  └── 调用 self._write_log(record)
        │
        ├── ApiLogger.instance().log(record)
        │     ├── 注入 test_run_id / pytest_nodeid / env
        │     ├── 递归脱敏 request_headers / request_body
        │     └── MongoSink.write(record) → 入队 → 后台批量写 Mongo
        │                                      → （降级）JsonlSink
        │
        └── GlobalContext.set("_last_trace_id", trace_id)
            GlobalContext.set("_recent_api_logs", recent[-5:])
                │
                └── 用例失败时由 conftest 读取并附加到 Allure 报告
```

---

## 八、生命周期管理（conftest 钩子）

### 8.1 Session 级初始化（`tests/conftest.py`）

```python
@pytest.fixture(scope="session", autouse=True)
def api_log_session(request):
    """Session 开始时初始化 ApiLogger，结束时 flush + 关闭。"""
    jsonl_sink = JsonlSink(API_LOGS_DIR)
    mongo_sink = MongoSink(
        uri=cfg.logging.mongo_uri,
        db_name=cfg.logging.mongo_db,
        collection_name=cfg.logging.mongo_collection,
        fallback_sink=jsonl_sink,
    )
    ApiLogger.initialize(sink=mongo_sink, env=cfg.env)

    yield

    ApiLogger.shutdown()   # flush() + close()：确保 session 结束时所有日志落盘
```

### 8.2 用例级 nodeid 注入（pytest hook）

```python
def pytest_runtest_setup(item):
    """每条用例开始前，将当前 nodeid 注入 ApiLogger，记录到 ApiLogRecord。"""
    api_logger = ApiLogger.instance()
    if api_logger:
        api_logger.set_current_nodeid(item.nodeid)
```

### 8.3 用例失败时附加日志摘要（conftest hook）

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        ctx = GlobalContext.instance()
        # 附加最近 5 条 API 链路摘要
        recent_logs = ctx.get("_recent_api_logs") or []
        allure.attach(
            body=json.dumps(recent_logs, ...) ,
            name="最近 API 链路摘要",
            attachment_type=allure.attachment_type.JSON,
        )
        # 附加最后 trace_id
        last_trace = ctx.get("_last_trace_id")
        if last_trace:
            allure.attach(body=last_trace, name="last_trace_id", ...)
```

### 8.4 生命周期时序图

```text
pytest session 开始
  │
  ├── conftest.api_log_session() 初始化
  │     MongoSink 后台 worker 启动
  │
  ├── pytest_runtest_setup(item)
  │     ApiLogger.set_current_nodeid(item.nodeid)
  │
  ├── 用例执行 → 每次 HTTP 请求 → ApiLogRecord 入队
  │
  ├── pytest_runtest_makereport（失败时）
  │     读 GlobalContext._recent_api_logs / _last_trace_id → 附加 Allure
  │
  ├── ... 下一条用例 ...
  │
  └── pytest session 结束
        ApiLogger.shutdown()
          ├── MongoSink.flush()  （阻塞等待当前批次写完，最多 10s）
          └── MongoSink.close()  （worker 退出，清空队列剩余记录）
```

---

## 九、GlobalContext：链路快照

`GlobalContext`（`core/context.py`）是线程安全的 KV 存储，用于在测试用例内跨步骤传递变量。日志体系利用它做失败时的快速回溯。

### 9.1 日志相关的 Context 字段

| Key | 类型 | 写入时机 | 读取时机 |
| --- | --- | --- | --- |
| `_last_trace_id` | `str` | 每次 HTTP 请求后（RequestWrapper） | 用例失败时（conftest hook） |
| `_recent_api_logs` | `list[dict]` | 每次 HTTP 请求后，保留最近 5 条 | 用例失败时（conftest hook） |

### 9.2 `_recent_api_logs` 摘要字段

```python
{
    "trace_id": "...",
    "method": "POST",
    "url": "http://localhost:1024/dev-api/system/user",
    "status_code": 200,
    "elapsed_ms": 45.2,
    "result": "success",          # success | fail | error
    "error_type": "",
    "error_message": "",
}
```

---

## 十、result 结果分类详解

| result 值 | 触发场景 | 对应 error_type 示例 |
| --- | --- | --- |
| `success` | HTTP 请求成功，响应 JSON 解析正常 | — |
| `fail` | 业务级异常（自定义 biz_code 命中） | `AuthError` / `APIPermissionError` / `BusinessConflictError` / `RateLimitError` |
| `error` | 环境/代码级异常，或网络层异常 | `Timeout` / `ConnectionError` / `EnvError` / `BugError` |

```text
HTTP 请求成功
  ├── 解析 JSON 成功 → result=success
  ├── biz_code 命中（98880/98881/98882/98883）→ result=fail，抛出 FinanceAPIError
  └── JSON 解析失败 → result=error，抛出 BugError

HTTP 502/503 → result=error，抛出 EnvError
HTTP 500
  ├── body 含合法 biz_code → result=success（降级为业务响应，code=500 交给用例层断言）
  └── body 无合法 biz_code → result=error，抛出 BugError

网络超时 → result=error，error_type=Timeout
连接失败 → result=error，error_type=ConnectionError
```

---

## 十一、MongoDB 查询与排障

Mongo 可用时，可按以下字段检索日志：

```javascript
// 按 trace_id 查单次请求
db.api_logs.findOne({ trace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" })

// 查某条用例的全部请求
db.api_logs.find({ pytest_nodeid: "tests/test_system/test_add_user.py::TestAddUser::test_add_user_required_fields_only" })

// 查本次 session 的所有失败请求
db.api_logs.find({ test_run_id: "...", result: { $ne: "success" } })

// 查耗时超过 3 秒的请求（性能排查）
db.api_logs.find({ elapsed_ms: { $gt: 3000 } })

// 查某业务类型的全部记录
db.api_logs.find({ business_type: "system:user:add" })
```

推荐索引：

```javascript
db.api_logs.createIndex({ trace_id: 1 }, { unique: true })
db.api_logs.createIndex({ test_run_id: 1, result: 1 })
db.api_logs.createIndex({ pytest_nodeid: 1 })
db.api_logs.createIndex({ created_at: -1 }, { expireAfterSeconds: 2592000 }) // TTL 30天
```

---

## 十二、JSONL 降级文件查询

Mongo 不可用时，日志写入 `outputs/api_logs/fallback_YYYY-MM-DD.jsonl`，可用标准命令行工具查询：

```bash
# 查某 trace_id
grep '"trace_id": "xxx"' outputs/api_logs/fallback_2026-05-05.jsonl | python3 -m json.tool

# 查所有失败请求
grep '"result": "fail"' outputs/api_logs/fallback_2026-05-05.jsonl

# 查某接口所有记录
grep '"api_name": "add_user"' outputs/api_logs/fallback_2026-05-05.jsonl | wc -l

# 统计今日请求数
wc -l outputs/api_logs/fallback_2026-05-05.jsonl
```

---

## 十三、排障路径（失败用例回溯）

```text
1. 查看 pytest 输出的失败堆栈
      ↓
2. 打开 Allure 报告
   → 查看 step 展开定位失败位置
   → 查看 "最近 API 链路摘要" 附件（JSON）
   → 复制 last_trace_id
      ↓
3. 按 trace_id 查 Mongo（或 grep JSONL）
   → 查看完整请求体、响应体、耗时
      ↓
4. 查 outputs/logs/finance_auto_YYYY-MM-DD.log
   → 搜索 [TC-XXX-NNN] 前缀的用例日志
      ↓
5. DB 回查 sys_* 表
   → 确认数据最终态（del_flag / status / 关联表残留）
```

---

## 十四、扩展指南

### 新增脱敏字段

在 `utils/api_logger.py` 的 `_DEFAULT_SENSITIVE_KEYS` 中添加：

```python
_DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset({
    ...,
    "bank_card",   # 新增银行卡字段脱敏
    "otp_code",    # 新增 OTP 验证码脱敏
})
```

### 新增业务元数据字段

1. 在 `ApiLogRecord` dataclass 中添加字段。
2. 在 `RequestWrapper._request()` 中从 `kwargs` pop 并赋值。
3. 在 `API 方法调用` 中传入 `_xxx=value`。

### 切换为其他存储后端

1. 实现 `LogSink` ABC（`write / flush / close` 三个方法）。
2. 在 `conftest.api_log_session` 中替换 `MongoSink` 实例化。
3. 新 Sink 同样需支持 `close()` 时刷盘。

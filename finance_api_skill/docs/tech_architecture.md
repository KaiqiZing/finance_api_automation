# 技术架构

## 一、项目定位与技术栈

当前项目是基于 Python 的接口自动化工程，面向 RuoYi 若依后端的 system 模块，核心技术栈为：

| 技术 | 版本要求 | 用途 |
| --- | --- | --- |
| `pytest` | ≥ 7.x | 测试执行、fixture、hook、marker、xdist 并发 |
| `requests` | — | HTTP 请求发送 |
| `allure-pytest` | — | 测试报告、step、attachment |
| `PyYAML` | — | 环境配置和请求体模板 |
| `loguru` | — | 运行时日志（双 Sink：控制台 + 文件） |
| `PyMySQL` | — | 数据库连接与 SQL 校验 |
| `pymongo` | — | API 结构化日志主存储（可选） |
| `jsonschema` | — | 响应 JSON Schema 契约校验 |
| `deepdiff` | — | 深度字段比对 |
| `cachetools` | — | TemplateManager LRU 缓存 |

---

## 二、整体架构全景图

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                           finance_api_automation                          │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  层 1  执行入口层                                                  │   │
│  │  run.py  ──  pytest.ini                                           │   │
│  │  --env / --mark / -n / --report                                   │   │
│  └───────────────────────┬──────────────────────────────────────────┘   │
│                           │                                               │
│  ┌────────────────────────▼─────────────────────────────────────────┐   │
│  │  层 2  测试治理层                                                  │   │
│  │  tests/conftest.py           tests/test_system/conftest.py        │   │
│  │  ・session 级 DB 健康检查     ・system 模块局部 fixture              │   │
│  │  ・ApiLogger 初始化/关闭      ・_login_and_get_token()              │   │
│  │  ・GlobalContext 隔离清理     ・只检查 ry_cloud                      │   │
│  │  ・失败时 Allure 附件挂载                                           │   │
│  └───────────────────────┬──────────────────────────────────────────┘   │
│                           │                                               │
│  ┌────────────────────────▼─────────────────────────────────────────┐   │
│  │  层 3  业务编排层                                                  │   │
│  │  business/system_flows.py                                         │   │
│  │  ・封装跨接口链路（login + get_info）                               │   │
│  │  ・写入 GlobalContext / 挂 Allure step                              │   │
│  └───────────────────────┬──────────────────────────────────────────┘   │
│                           │                                               │
│  ┌────────────────────────▼─────────────────────────────────────────┐   │
│  │  层 4  原子 API 层                                                 │   │
│  │  api/base_api.py       api/system/base_system_api.py              │   │
│  │  api/system/login_api.py                                          │   │
│  │  api/system/user_api.py  role_api.py  post_api.py                 │   │
│  │  api/system/dept_api.py  notice_api.py                            │   │
│  │  ・单资源封装，不写业务流                                            │   │
│  │  ・_build_payload() → RequestWrapper.post/get/put/delete()        │   │
│  └──────┬──────────────────────────┬──────────────────────────────-─┘   │
│         │                          │                                      │
│  ┌──────▼───────┐         ┌────────▼──────────────────────────────┐     │
│  │  层 5  数据层 │         │  层 6  核心引擎层                       │     │
│  │              │         │                                         │     │
│  │  data/       │         │  core/request_wrapper.py  RequestWrapper│     │
│  │  templates/  │──load──>│  core/template_manager.py TemplateManager│   │
│  │  *.yaml      │         │  core/data_engine.py      DataEngine    │     │
│  │              │         │  core/context.py           GlobalContext │     │
│  │  data/       │         │  core/validator.py         Validator    │     │
│  │  schemas/    │──valid─>│  core/settings.py          路径常量      │     │
│  │  *.json      │         │                                         │     │
│  └──────────────┘         └────────────────────────────────────────┘     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  层 7  配置层                                                      │   │
│  │  config/settings.py  AppConfig（单例）                             │   │
│  │  config/env_dev.yaml / env_test.yaml                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  层 8  基础设施层（utils/）                                         │   │
│  │  db_client.py       数据库注册、查询、健康检查                        │   │
│  │  api_logger.py      ApiLogger 结构化日志（Mongo 主 + JSONL 降级）   │   │
│  │  logger.py          loguru 运行时日志                               │   │
│  │  system_ruoyi_queries.py  RuoYi sys_* 表 DB 辅助查询               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 三、分层职责详解

### 层 1：执行入口层

**关键文件：** `run.py`、`pytest.ini`

```bash
python3 run.py                          # 默认 dev 环境，全量用例
python3 run.py --env test               # 切换到 test 环境
python3 run.py --mark smoke             # 只跑冒烟用例
python3 run.py --mark scenario -n 1    # 并发数为 1 的场景测试
python3 run.py --env test --report      # 执行后自动打开 Allure 报告
```

职责：

- 解析 `--env` 设置 `TEST_ENV` 环境变量，触发 `AppConfig` 加载对应 YAML。
- 解析 `--mark` 透传给 pytest `-m` 过滤用例。
- `-n` 参数启用 `pytest-xdist` 多进程并发（DB 和 API 均线程/进程安全）。
- Allure 原始结果输出到 `outputs/allure_results/`，`--report` 时调用 `allure serve`。

---

### 层 2：测试治理层

**关键文件：** `tests/conftest.py`、`tests/test_system/conftest.py`

#### 全局 conftest.py 的四个职责

| Hook / Fixture | 作用域 | 职责 |
| --- | --- | --- |
| `pytest_sessionstart` | session | 初始化 ApiLogger（MongoSink 主 + JsonlSink 降级） |
| `pytest_runtest_setup` | 每条用例 | 注入当前 nodeid 到 ApiLogger |
| `pytest_sessionfinish` | session | flush + close ApiLogger，日志全部落盘 |
| `db_health_check` fixture | session | 注册并健康检查所有 DB，失败则 `pytest.exit` 终止 |
| `reset_global_context` fixture | function | 每条用例结束后清空 GlobalContext |
| `pytest_runtest_makereport` hook | 每条用例 | 失败时向 Allure 挂载 GlobalContext 快照 + API 链路摘要 |

#### system 模块 conftest.py

- 局部覆盖 `db_health_check`，只检查 `ry_cloud` 数据库（避免全局检查阻塞）。
- 提供 `_login_and_get_token()`：调用登录接口获取 token，session 内可复用。
- 提供 `gen_username()` / `gen_phone()` 等测试数据生成工具函数。

---

### 层 3：业务编排层

**关键文件：** `business/system_flows.py`

```text
SystemFlows.login_and_get_info()
  ├── do_login()
  │     SystemLoginAPI.login()
  │       └── GlobalContext.set("system_token", token)
  │       └── GlobalContext.set("system_username", username)
  └── do_get_info()
        SystemUserAPI.get_info()
          └── GlobalContext.set("userId", ...)
          └── GlobalContext.set("roles", [...])
          └── GlobalContext.set("permissions", [...])
```

规则：

- 只沉淀**跨接口复用**的链路，一次性的测试场景保留在用例层。
- 每个关键步骤用 `allure.step` 包裹，变量写入 `GlobalContext` 供后续接口用 `$CONTEXT{key}` 引用。

---

### 层 4：原子 API 层

**继承关系：**

```text
BaseAPI
  └── SystemBaseAPI（从 cfg.system_api 读 base_url）
        ├── SystemLoginAPI
        ├── SystemUserAPI
        ├── SystemRoleAPI
        ├── SystemPostAPI
        ├── SystemDeptAPI
        └── SystemNoticeAPI
```

**BaseAPI 核心方法：**

```python
def _build_payload(module, template_name, overrides) -> dict:
    tpl = TemplateManager.instance().load(module, template_name)   # 加载 YAML 深拷贝
    rendered = DataEngine().render(tpl, overrides)                 # 渲染动态标签
    return rendered.get("payload", rendered)                       # 取 payload 节点

def set_token(token: str) -> None:
    self._wrapper.set_token(token)   # 注入 Bearer Token
```

API 方法只做两件事：**构建 payload** 和**调用 RequestWrapper**，不做断言、不写 GlobalContext、不直接查 DB。

---

### 层 5：数据层

**目录：** `data/templates/`（YAML 请求体模板）、`data/schemas/`（JSON Schema）

YAML 模板结构：

```yaml
payload:
  userName: "${rand_str(en, 8)}"
  nickName: "${rand_str(chn, 4)}"
  password: "Test@123456"
  status: "0"
  remark: "自动化_${uuid}"
```

已支持的动态标签（由 DataEngine 解析）：

| 标签 | 输出 |
| --- | --- |
| `${rand_str(chn, N)}` | N 个随机汉字 |
| `${rand_str(en, N)}` | N 个随机英文字母 |
| `${rand_str(num, N)}` | N 个随机数字 |
| `${rand_str(mix, N)}` | N 个字母+数字混合 |
| `${get_mobile}` | 随机手机号 |
| `${get_id_card}` | 随机 18 位身份证号 |
| `${get_bank_card}` | 随机银行卡号 |
| `${get_name}` | 随机中文姓名 |
| `${choice(['a','b'])}` | 列表中随机取一项 |
| `${gen_id_by_type(01)}` | 按证件类型生成证件号 |
| `${timestamp}` | 当前 Unix 时间戳 |
| `${uuid}` | UUID4 字符串 |
| `$CONTEXT{key}` | 从 GlobalContext 读取变量 |

---

### 层 6：核心引擎层

#### RequestWrapper

职责：统一 HTTP session、token 注入、trace_id 生成、重试策略、响应错误分类、日志写入。

关键配置：

```python
RequestConfig(
    timeout=30,             # 请求超时秒数
    max_retries=3,          # 重试次数（针对 502/503/504）
    retry_backoff=0.5,      # 重试退避系数
    verify_ssl=False,       # 忽略 SSL 证书
    extra_headers={},       # 额外请求头
)
```

响应错误分类：

| HTTP 状态 / biz_code | 分类 | 异常类 | 处理 |
| --- | --- | --- | --- |
| `98880` | 权限缺失 | `APIPermissionError` | 抛出，测试层捕获 |
| `98881` | Token 失效 | `AuthError` | 抛出，测试层捕获 |
| `98882` | 业务互斥 | `BusinessConflictError` | 抛出，测试层捕获 |
| `98883` | 频控拦截 | `RateLimitError` | 抛出，测试层捕获 |
| `500`（含业务 JSON） | 业务失败 | 无（降级为正常响应） | code=500 透传给用例断言 |
| `500`（无业务 JSON） | 代码 Bug | `BugError` | 抛出 |
| `502/503` | 环境异常 | `EnvError` | 抛出 |
| Timeout | 网络超时 | `EnvError` | 抛出 |

#### TemplateManager

- **单例 + 双重检测锁**，进程内只有一个实例。
- **LRU 缓存**（上限 256 条），首次加载磁盘，后续命中缓存。
- **返回深拷贝**，防止多用例间 YAML 数据污染。

#### DataEngine

- **两阶段渲染**：先 `_apply_overrides`（用例层覆盖点分路径字段），再 `_resolve`（递归解析动态标签）。
- 对整个标签（如 `"${uuid}"`）保留原始类型（int/str/list），对内嵌标签做字符串插值。

#### GlobalContext

- **单例 + RLock**，线程安全的全局 KV 存储。
- `set/get/update/clear/snapshot` 五类接口。
- `get_required(key)` 在 key 不存在时抛出 `KeyError`（用于 `$CONTEXT{key}` 标签强制依赖检查）。
- `conftest.reset_global_context` 在每条用例结束后调用 `clear()`，保证用例隔离。

#### Validator

五种断言能力：

| 方法 | 断言类型 |
| --- | --- |
| `assert_status_code(resp, expected)` | HTTP 状态码（从 `_status_code` 字段读取） |
| `assert_success(body)` / `assert_ruoyi_success(body)` | 业务成功码（code == 200） |
| `assert_field(body, "data.account_no", expected)` | 响应字段精确匹配（支持点分路径） |
| `assert_schema(body, "schema_name")` | JSON Schema 结构契约校验 |
| `assert_db_field(sql, expected, timeout=30)` | DB 轮询断言（适用 MQ 异步场景） |

---

### 层 7：配置层

**关键文件：** `config/settings.py`（`AppConfig` 单例）、`config/env_dev.yaml`、`config/env_test.yaml`

```text
AppConfig（懒加载单例）
  ├── cfg.env              → "dev" / "test"
  ├── cfg.api              → base_url / timeout / max_retries / verify_ssl
  ├── cfg.system_api       → RuoYi system 模块专属 base_url
  ├── cfg.auth             → 默认账号（用于登录）
  ├── cfg.databases        → alias → host/port/user/password/db
  ├── cfg.logging          → mongo.enabled / mongo.uri / fallback_dir / sensitive_keys
  └── cfg.allure_meta      → epic / env_name（注入 Allure 报告 Environment 面板）
```

切换规则：

- `TEST_ENV=dev`（默认） → 加载 `config/env_dev.yaml`
- `TEST_ENV=test` / `run.py --env test` → 加载 `config/env_test.yaml`
- 不要在测试用例中硬编码 base_url / DB 连接，统一从 `cfg` 读取。

---

### 层 8：基础设施层（utils/）

| 文件 | 核心对象 | 职责 |
| --- | --- | --- |
| `logger.py` | `logger`（loguru） | 运行时日志，控制台 INFO + 文件 DEBUG，幂等初始化 |
| `api_logger.py` | `ApiLogger` | 结构化 API 日志单例，MongoSink 异步批量 + JsonlSink 降级 |
| `db_client.py` | `DBClient` | MySQL 连接池，注册/查询/健康检查 |
| `system_ruoyi_queries.py` | 函数集 | RuoYi sys_* 表常用 DB 查询和数据清理辅助 |

---

## 四、核心数据流

### 4.1 HTTP 请求完整数据流

```text
测试用例方法
│
│  user_api.add_user(user_name="xxx", nick_name="yyy", password="zzz")
│
▼
SystemUserAPI.add_user()
│
│  overrides = {"payload.userName": "xxx", "payload.nickName": "yyy"}
│  payload = self._build_payload("system", "add_user", overrides)
│
▼
BaseAPI._build_payload()
│
│  ① TemplateManager.load("system", "add_user")
│     ├── 检查 LRU 缓存（命中 → 直接返回深拷贝）
│     └── 未命中 → 读取 data/templates/system/add_user.yaml → 写入缓存 → 返回深拷贝
│
│  ② DataEngine.render(tpl, overrides)
│     ├── _apply_overrides(tpl, overrides)
│     │     点分路径 "payload.userName" → tpl["payload"]["userName"] = "xxx"
│     └── _resolve(tpl)（递归）
│           字符串遇到 ${uuid} → 生成 UUID4
│           字符串遇到 $CONTEXT{key} → 从 GlobalContext 读取
│
│  ③ 返回 rendered["payload"]（去掉外层 payload 包装）
│
▼
RequestWrapper.post("/system/user", json=payload, _module="system",
                    _api_name="add_user", _business_type="system:user:add",
                    _service="ruoyi")
│
│  ① 摘取 _module / _api_name / _business_type / _service（不传给 requests）
│  ② trace_id = str(uuid.uuid4())
│  ③ 注入请求头 X-Trace-Id: {trace_id}
│  ④ 构建 ApiLogRecord（trace_id + 请求信息 + 业务元数据）
│  ⑤ session.request("POST", url, json=payload, headers={...}, timeout=30, ...)
│
▼
（HTTP 响应返回）
│
│  ① elapsed_ms = (time.monotonic() - start) * 1000
│  ② resp.status_code 写入 record
│  ③ _handle_response(resp)
│     ├── HTTP 502/503 → EnvError
│     ├── HTTP 500 + 有业务 JSON → 透传（code=500 交给用例断言）
│     ├── HTTP 500 + 无业务 JSON → BugError
│     ├── biz_code 命中 _BIZ_CODE_MAP → 抛出 FinanceAPIError 子类（result=fail）
│     └── 正常 → 返回 body dict（result=success）
│
▼
_write_log(record)
│
│  ① ApiLogger.instance().log(record)
│     ├── 补全 test_run_id / pytest_nodeid / env
│     ├── mask_sensitive(request_headers)  （Authorization → ***）
│     ├── mask_sensitive(request_body)    （password → ***）
│     └── MongoSink.write(record) → queue.put_nowait → 后台 worker 批量写 Mongo
│                                   （队列满 / Mongo 不可用 → JsonlSink 降级）
│
│  ② GlobalContext.set("_last_trace_id", trace_id)
│     GlobalContext.set("_recent_api_logs", recent[-5:])
│
▼
返回 body dict 给测试用例
│
│  with allure.step("断言 code == 200"):
│      assert resp.get("code") == 200, f"code={resp.get('code')}, msg={resp.get('msg')}"
```

---

### 4.2 Payload 构建数据流（渲染细节）

```text
YAML 原始模板（磁盘文件）
┌──────────────────────────────────────┐
│ payload:                             │
│   userName: "${rand_str(en, 8)}"     │
│   nickName: "${rand_str(chn, 4)}"    │
│   password: "Test@123456"            │
│   deptId: null                       │
│   roleIds: [0]                       │
│   remark: "自动化_${uuid}"           │
└──────────────────────────────────────┘
          │ TemplateManager.load()（深拷贝）
          ▼
YAML 深拷贝（内存）
          │
          │ DataEngine._apply_overrides(overrides={
          │     "payload.userName": "auto_usr123",
          │     "payload.deptId": 103,
          │     "payload.roleIds": [2]
          │ })
          ▼
覆盖后的模板
┌──────────────────────────────────────┐
│ payload:                             │
│   userName: "auto_usr123"            │← 被 overrides 覆盖
│   nickName: "${rand_str(chn, 4)}"    │← 待渲染
│   password: "Test@123456"            │← 保持原值
│   deptId: 103                        │← 被 overrides 覆盖
│   roleIds: [2]                       │← 被 overrides 覆盖
│   remark: "自动化_${uuid}"           │← 待渲染
└──────────────────────────────────────┘
          │ DataEngine._resolve()（递归）
          ▼
渲染后的 payload（直接用于 HTTP 请求体）
┌──────────────────────────────────────┐
│ userName: "auto_usr123"              │
│ nickName: "云梦浩"                    │← rand_str 生成
│ password: "Test@123456"              │
│ deptId: 103                          │
│ roleIds: [2]                         │
│ remark: "自动化_a3f9b..."            │← uuid 生成
└──────────────────────────────────────┘
```

---

### 4.3 Session 生命周期与 fixture 触发顺序

```text
pytest session 启动
│
├─ pytest_sessionstart（Hook）
│   └── ApiLogger.initialize(MongoSink / JsonlSink)
│         MongoSink 后台 worker 线程启动
│
├─ db_health_check fixture（session scope, autouse）
│   └── 遍历 cfg.databases，DBClient.register + health_check
│         失败 → pytest.exit（终止整个 session）
│
├─ pytest_configure（Hook）
│   └── 注入 Allure Environment 面板（EPIC / ENV_NAME）
│
│ ┌── 每条用例 ────────────────────────────────────────────────┐
│ │                                                            │
│ │ pytest_runtest_setup（Hook）                               │
│ │   └── ApiLogger.set_current_nodeid(item.nodeid)           │
│ │                                                            │
│ │ reset_global_context fixture（function scope, autouse）    │
│ │   └── yield（用例执行）                                     │
│ │         └── 用例内所有 HTTP 请求 → RequestWrapper → ApiLogger│
│ │   └── GlobalContext.instance().clear()（用例结束后）         │
│ │                                                            │
│ │ pytest_runtest_makereport（Hook, tryfirst）                │
│ │   └── 仅 report.failed == True 时触发：                    │
│ │         ① allure.attach(GlobalContext 业务快照)            │
│ │         ② allure.attach(last_trace_id + 最近 5 条 API 摘要)│
│ └────────────────────────────────────────────────────────────┘
│
└─ pytest_sessionfinish（Hook）
    └── ApiLogger.shutdown()
          ├── MongoSink.flush()（阻塞最多 10s，等当前批次写完）
          └── MongoSink.close()（worker 退出，清空剩余队列）
```

---

### 4.4 用例失败时的 Allure 附件数据流

```text
用例执行失败（assert 抛出 AssertionError）
│
▼
pytest_runtest_makereport（conftest Hook，tryfirst）
│
│  ctx = GlobalContext.instance()
│  snapshot = ctx.snapshot()     ← 当前用例所有写入的业务变量
│
├─ 附件 1：GlobalContext 业务快照（JSON）
│   ├── 过滤掉 _ 前缀内部字段（_last_trace_id / _recent_api_logs）
│   └── 保留业务字段（apply_no / system_token / userId / ...）
│
├─ 附件 2：API 链路追踪摘要（JSON）
│   ├── last_trace_id（最后一次 HTTP 请求的 trace_id）
│   ├── mongo_query_hint（MongoDB 查询语句提示）
│   └── recent_api_requests（最近 5 条请求摘要：method/url/status/elapsed_ms/result）
│
▼
Allure 报告
  └── 失败用例详情页
        ├── step 展开（定位失败位置）
        ├── GlobalContext 快照（查业务变量）
        └── API 链路追踪（复制 trace_id → 查 Mongo / grep JSONL）
```

---

### 4.5 API 结构化日志数据流

```text
RequestWrapper._write_log(record)
│
├─ ApiLogger.log(record)
│   ├── record.test_run_id   ← session 级别唯一 ID
│   ├── record.pytest_nodeid ← 当前用例 nodeid
│   ├── record.env           ← "dev" / "test"
│   ├── mask_sensitive(request_headers)  Authorization → ***
│   ├── mask_sensitive(request_body)     password → ***
│   └── MongoSink.write(record)
│         │
│         ├── 正常：queue.put_nowait(record)
│         │         后台 worker 轮询（每 0.2s）
│         │         ├── 积压 ≥ 20 条 → insert_many 批量写 Mongo
│         │         ├── 距上次写 ≥ 2s → insert_many 批量写 Mongo
│         │         └── flush_event 触发 → insert_many + 通知完成
│         │
│         ├── Mongo 不可用（降级）：JsonlSink.write(record)
│         │         └── outputs/api_logs/fallback_YYYY-MM-DD.jsonl（追加写，加锁）
│         │
│         └── 队列满：直接 JsonlSink.write(record)（不阻塞）
│
└─ GlobalContext.set("_last_trace_id", trace_id)
   GlobalContext.set("_recent_api_logs", recent[-5:])（内存快照，用于 Allure 附件）
```

---

## 五、单例对象总览

| 对象 | 所在文件 | 单例模式 | 线程安全 | 生命周期 |
| --- | --- | --- | --- | --- |
| `AppConfig` | `config/settings.py` | 双重检测锁 | 是 | 进程启动到结束 |
| `TemplateManager` | `core/template_manager.py` | 双重检测锁 | 是（LRU 缓存为线程安全） | 进程启动到结束 |
| `GlobalContext` | `core/context.py` | 双重检测锁 + RLock | 是 | 每条用例结束清空，session 结束销毁 |
| `DBClient` | `utils/db_client.py` | 按 alias 注册 | 是（连接池） | session 开始注册，session 结束关闭 |
| `ApiLogger` | `utils/api_logger.py` | 类变量 + Lock | 是 | `pytest_sessionstart` 初始化，`pytest_sessionfinish` 关闭 |

---

## 六、错误处理与异常体系

```text
FinanceAPIError（基类）
  ├── APIPermissionError  （98880：无权限，测试层捕获后断言 msg）
  ├── AuthError           （98881：Token 失效，一般 pytest.fail）
  ├── BusinessConflictError（98882：业务互斥，测试层捕获后断言 msg）
  └── RateLimitError      （98883：频控，测试层捕获后断言）

EnvError                  （502/503/Timeout/ConnectionError：环境问题，不算 Bug）
BugError                  （500 无业务 JSON / JSON 解析失败：代码 Bug）
ValidationAssertionError  （Validator 断言失败，携带 Diff 信息）
```

测试层对异常的处理原则：

- `FinanceAPIError` 子类：在 **异常场景用例** 中捕获并断言具体 msg，在 **正向用例** 中不捕获（直接报错）。
- `EnvError`：视作环境问题，排查环境后重跑，不算 Bug。
- `BugError`：视作代码 Bug，记录到 Allure 并提交缺陷。
- 测试用例本身的 `AssertionError`：通过 `pytest_runtest_makereport` hook 挂载 Allure 诊断附件。

---

## 七、关键路径常量（core/settings.py）

```text
BASE_DIR        /Users/.../finance_api_automation/
CONFIG_DIR      BASE_DIR/config/
DATA_DIR        BASE_DIR/data/
TEMPLATES_DIR   DATA_DIR/templates/             ← YAML 模板根目录
SCHEMAS_DIR     DATA_DIR/schemas/               ← JSON Schema 根目录
OUTPUTS_DIR     BASE_DIR/outputs/
LOGS_DIR        OUTPUTS_DIR/logs/               ← loguru 文件日志
ALLURE_RESULTS  OUTPUTS_DIR/allure_results/     ← Allure 原始结果
API_LOGS_DIR    OUTPUTS_DIR/api_logs/           ← JSONL 降级日志
```

启动时自动创建 `LOGS_DIR`、`ALLURE_RESULTS_DIR`、`API_LOGS_DIR`，无需手动建目录。

---

## 八、新增功能的标准路径

### 新增一个 system 资源接口

```text
步骤 1  data/templates/system/add_{resource}.yaml
         └── 写 payload 节点，必填字段用动态标签，可选字段给合理默认值

步骤 2  data/templates/system/update_{resource}.yaml
         └── 增加 {resource}Id: null 占位，由用例 overrides 覆盖

步骤 3  api/system/{resource}_api.py（继承 SystemBaseAPI）
         └── list / add / update / get / delete 五个方法
         └── 每个方法传 _module / _api_name / _business_type / _service

步骤 4  utils/system_ruoyi_queries.py
         └── 新增后接口不返回 ID 时，写 fetch_{resource}_id_by_{field}()

步骤 5  tests/test_system/test_{resource}_crud.py
         └── 正向 + 鉴权 + 业务互斥 + 数据驱动用例

步骤 6  （可选）tests/test_system/test_system_business_flows.py
         └── 涉及跨资源组合时新增业务流用例
```

### 新增环境配置

```text
步骤 1  在 config/env_{env}.yaml 增加新字段
步骤 2  在 AppConfig 属性中暴露访问入口
步骤 3  测试用例通过 cfg.xxx 读取，不硬编码
```

### 扩展动态标签

```text
步骤 1  在 DataEngine._dispatch() 中增加 if 分支
步骤 2  在 DataEngine 下方增加静态方法生成数据
步骤 3  在 tech_architecture.md 和 code_generation_templates.md 更新标签列表
```

---

## 九、失败排查路径

```text
① pytest 输出堆栈
   └── 定位失败的断言行和实际值

② Allure 报告（allure serve outputs/allure_results）
   └── 展开失败 step，查看 GlobalContext 快照和 API 链路摘要附件
   └── 复制 last_trace_id（8 位前缀可见）

③ MongoDB 精确查询
   db.api_logs.findOne({trace_id: "完整 trace_id"})
   └── 查看完整 request_body / response_body / elapsed_ms

④ JSONL 降级文件查询（Mongo 不可用时）
   grep '"trace_id": "xxx"' outputs/api_logs/fallback_YYYY-MM-DD.jsonl

⑤ 运行时日志
   grep "[TC-XXX-NNN]" outputs/logs/finance_auto_YYYY-MM-DD.log

⑥ DB 回查 sys_* 表
   SELECT del_flag, status FROM sys_user WHERE user_id = xxx;
   └── 确认数据最终态，区分接口 Bug 和数据 Bug
```

# 环境配置说明

本文档说明 `finance_api_automation` 项目当前使用的两套环境（`dev` / `test`）的完整配置结构、切换方式和各配置项含义。

> 注意：文档中涉及账号、密码、数据库地址的字段均已脱敏，真实值见 `config/env_*.yaml`，不要将真实凭据写入文档或提交到公开仓库。

---

## 一、环境切换方式

### 命令行切换（推荐）

```bash
python3 run.py                  # 默认加载 test 环境（TEST_ENV 未设置时默认 test）
python3 run.py --env dev        # 加载 config/env_dev.yaml
python3 run.py --env test       # 加载 config/env_test.yaml
```

### 环境变量切换

```bash
export TEST_ENV=dev
pytest tests/test_system/
```

### 加载逻辑（AppConfig 单例）

```python
# config/settings.py
env = os.environ.get("TEST_ENV", "test").lower()   # 默认 test
path = _CONFIG_DIR / f"env_{env}.yaml"             # 加载对应文件
```

`AppConfig` 是双重检测锁单例，进程内只加载一次。强制重建（如切换环境）需调用 `AppConfig.reset(env)`。

---

## 二、配置文件结构总览

```text
config/
  env_dev.yaml        开发环境
  env_test.yaml       测试环境
  settings.py         AppConfig 单例加载器
```

两个 YAML 文件结构完全一致，只有具体值不同，字段说明见下文。

---

## 三、dev 环境配置（config/env_dev.yaml）

### 3.1 基础金融 API

```yaml
env: dev

api:
  base_url: "http://dev.finance-api.internal:8080"
  timeout: 30           # HTTP 请求超时秒数
  max_retries: 3        # 502/503/504 自动重试次数
  verify_ssl: false     # 忽略 SSL 证书（内网环境）
  extra_headers:
    X-Env: "dev"
    X-App-Id: "finance_auto"
```

### 3.2 鉴权配置

```yaml
auth:
  login_url: "/api/v1/auth/login"
  default_user: "test_admin"
  default_password: "***"       # 见 config/env_dev.yaml
```

### 3.3 RuoYi system 模块 API

```yaml
system_api:
  base_url: "http://192.168.0.107/dev-api"
  timeout: 15
  verify_ssl: false
  default_user: "admin"
  default_password: "***"       # 见 config/env_dev.yaml
```

> `system_api` 是 system 模块专属入口，`SystemBaseAPI` 读取此配置构建 `RequestWrapper`，与 `api.base_url`（金融业务 API）独立。

### 3.4 数据库

```yaml
databases:
  default:              # 金融核心库（主业务数据）
    host: "dev-mysql.internal"
    port: 3306
    user: "***"
    password: "***"
    database: "finance_core"
    charset: "utf8mb4"

  dict_db:              # 字典库
    host: "dev-mysql.internal"
    port: 3306
    user: "***"
    password: "***"
    database: "finance_dict"
    charset: "utf8mb4"

  ry_cloud:             # RuoYi 若依云数据库（system 模块专用）
    host: "192.168.0.107"
    port: 3306
    user: "root"
    password: "***"
    database: "ry-cloud"
    charset: "utf8mb4"
```

### 3.5 轮询器（异步场景 DB 断言）

```yaml
poller:
  timeout: 60           # 最大等待秒数（MQ 异步处理轮询上限）
  interval: 3.0         # 轮询间隔秒数
```

### 3.6 Allure 报告元数据

```yaml
allure:
  epic: "金融系统接口自动化"
  env_name: "开发环境(DEV)"   # 显示在 Allure 报告 Environment 面板
```

### 3.7 日志配置

```yaml
logging:
  mongo:
    enabled: true
    uri: "mongodb://192.168.0.107:27018"
    db_name: "finance_auto_logs"
    collection_name: "api_logs"
    batch_size: 20              # 批量写入条数阈值
    flush_interval_sec: 2       # 强制写入时间间隔（秒）
    queue_maxsize: 500          # 内存队列上限
    max_pool_size: 20           # MongoDB 连接池大小

  sensitive_keys:               # 日志脱敏字段（值替换为 ***）
    - password
    - passwd
    - pwd
    - token
    - access_token
    - refresh_token
    - authorization
    - secret
    - private_key
    - card_no
    - id_card
    - phone
    - mobile
    - id_number

  ttl_days: 0                   # 0 表示不启用 MongoDB TTL 自动过期索引
  fallback_dir: "outputs/api_logs"   # Mongo 不可用时的 JSONL 降级目录
```

---

## 四、test 环境配置（config/env_test.yaml）

### 4.1 基础金融 API

```yaml
env: test

api:
  base_url: "http://192.168.0.107/"
  timeout: 30
  max_retries: 3
  verify_ssl: false
  extra_headers:
    X-Env: "test"
    X-App-Id: "finance_auto"
```

### 4.2 鉴权配置

```yaml
auth:
  login_url: "/dev-api/auth/login"
  default_user: "admin"
  default_password: "***"       # 见 config/env_test.yaml
```

### 4.3 RuoYi system 模块 API

```yaml
system_api:
  base_url: "http://192.168.0.107/dev-api"
  timeout: 15
  verify_ssl: false
  default_user: "admin"
  default_password: "***"       # 见 config/env_test.yaml
```

### 4.4 数据库

```yaml
databases:
  default:
    host: "test-mysql.internal"
    port: 3306
    user: "***"
    password: "***"
    database: "finance_core"
    charset: "utf8mb4"

  dict_db:
    host: "test-mysql.internal"
    port: 3306
    user: "***"
    password: "***"
    database: "finance_dict"
    charset: "utf8mb4"

  ry_cloud:                     # 与 dev 环境共用同一台 MySQL 实例
    host: "192.168.0.107"
    port: 3306
    user: "root"
    password: "***"
    database: "ry-cloud"
    charset: "utf8mb4"
```

### 4.5 ~ 4.7 轮询器 / Allure / 日志

与 dev 环境完全一致，仅 `allure.env_name` 不同：

```yaml
allure:
  env_name: "测试环境(TEST)"
```

---

## 五、dev vs test 环境差异对比

| 配置项 | dev | test | 备注 |
| --- | --- | --- | --- |
| `env` 标识 | `dev` | `test` | AppConfig.env 返回值 |
| `api.base_url` | `http://dev.finance-api.internal:8080` | `http://192.168.0.107/` | 金融业务 API 地址 |
| `auth.login_url` | `/api/v1/auth/login` | `/dev-api/auth/login` | 登录接口路径 |
| `auth.default_user` | `test_admin` | `admin` | 默认登录账号 |
| `system_api.base_url` | `http://192.168.0.107/dev-api` | `http://192.168.0.107/dev-api` | **两环境相同** |
| `databases.default.host` | `dev-mysql.internal` | `test-mysql.internal` | 金融核心库 |
| `databases.dict_db.host` | `dev-mysql.internal` | `test-mysql.internal` | 字典库 |
| `databases.ry_cloud.host` | `192.168.0.107` | `192.168.0.107` | **两环境相同** |
| `allure.env_name` | `开发环境(DEV)` | `测试环境(TEST)` | Allure 报告显示 |
| `logging.mongo.uri` | `mongodb://192.168.0.107:27018` | `mongodb://192.168.0.107:27018` | **两环境相同** |
| `X-Env` 请求头 | `dev` | `test` | 注入每个 HTTP 请求 |

**当前 system 模块实际使用情况：**

- `system_api`、`databases.ry_cloud`、`logging.mongo` 三组配置在 dev/test 两套环境中指向**同一台服务器**（`192.168.0.107`）。
- `databases.default` 和 `databases.dict_db` 指向不同的 MySQL host，但 system 测试用例目前只使用 `ry_cloud`。

---

## 六、各配置项的代码访问路径

```python
from config.settings import cfg

# 当前环境标识
cfg.env                          # "dev" 或 "test"

# 金融业务 API
cfg.api["base_url"]              # HTTP base_url
cfg.api["timeout"]               # 请求超时
cfg.api["extra_headers"]         # 额外请求头（含 X-Env / X-App-Id）

# 鉴权
cfg.auth["login_url"]            # 登录接口路径
cfg.auth["default_user"]         # 默认账号
cfg.auth["default_password"]     # 默认密码（已脱敏，实际读 YAML）

# RuoYi system API
cfg.get("system_api")["base_url"]        # system 模块 base_url
cfg.get("system_api")["default_user"]    # system 默认账号

# 数据库
cfg.databases["default"]         # 金融核心库连接参数
cfg.databases["dict_db"]         # 字典库连接参数
cfg.databases["ry_cloud"]        # RuoYi 若依库连接参数（system 模块专用）

# 轮询器
cfg.poller["timeout"]            # 最大等待秒数
cfg.poller["interval"]           # 轮询间隔

# Allure 元数据
cfg.allure_meta["epic"]          # Allure Epic 标签
cfg.allure_meta["env_name"]      # Allure Environment 面板环境名

# 日志
cfg.logging["mongo"]["enabled"]            # MongoDB 日志是否启用
cfg.logging["mongo"]["uri"]               # MongoDB 连接 URI
cfg.logging["fallback_dir"]               # JSONL 降级目录
cfg.logging["sensitive_keys"]             # 脱敏字段列表
```

---

## 七、数据库连接初始化流程

`DBClient` 在 `conftest.db_health_check` fixture（session 级）中注册并健康检查：

```python
# tests/conftest.py（简化）
for alias, db_cfg in cfg.databases.items():
    DBClient.register(alias, db_cfg)      # 注册连接参数（不立即建连）
    DBClient.instance(alias).health_check()  # 执行 SELECT 1，失败则 pytest.exit
```

system 模块的 `tests/test_system/conftest.py` 局部覆盖，只检查 `ry_cloud`：

```python
# 只注册 ry_cloud，避免 default/dict_db 不可用时阻断 system 测试
DBClient.register("ry_cloud", cfg.databases["ry_cloud"])
DBClient.instance("ry_cloud").health_check()
```

测试用例中直接按 alias 获取连接：

```python
from utils.db_client import DBClient

db = DBClient.instance("ry_cloud")
row = db.fetch_one("SELECT user_id FROM sys_user WHERE user_name = %s LIMIT 1", ("admin",))
```

---

## 八、MongoDB 日志服务连接信息

| 属性 | 值 |
| --- | --- |
| 连接 URI | `mongodb://192.168.0.107:27018` |
| 数据库名 | `finance_auto_logs` |
| 集合名 | `api_logs` |
| 两环境共用 | 是（dev/test 写同一个 Mongo 实例，通过 `env` 字段区分） |
| 连接失败策略 | 自动降级到 JSONL，不影响测试执行 |
| JSONL 降级路径 | `outputs/api_logs/fallback_YYYY-MM-DD.jsonl` |

常用 Mongo 查询：

```javascript
// 查询当前 session 所有 test 环境的失败记录
db.api_logs.find({ env: "test", result: { $ne: "success" } })

// 按 trace_id 查单次请求完整记录
db.api_logs.findOne({ trace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" })

// 查某业务类型今日的全部请求
db.api_logs.find({
  business_type: "system:user:add",
  created_at: { $gte: new Date("2026-05-05T00:00:00Z") }
})

// 查某条用例的全部 HTTP 调用
db.api_logs.find({
  pytest_nodeid: "tests/test_system/test_add_user.py::TestAddUser::test_add_user_required_fields_only"
})
```

---

## 九、新增环境的操作步骤

如需增加 `staging` 环境：

```bash
# 1. 复制并修改配置文件
cp config/env_test.yaml config/env_staging.yaml
# 修改 env_staging.yaml 中的 env: staging 及各服务地址

# 2. 运行时指定环境
python3 run.py --env staging
# 或
TEST_ENV=staging pytest tests/test_system/
```

`AppConfig._load()` 会自动查找 `config/env_staging.yaml`，无需修改代码。

---

## 十、常见环境问题排查

| 问题现象 | 可能原因 | 解决方法 |
| --- | --- | --- |
| `pytest.exit: 数据库 'ry_cloud' 健康检查失败` | MySQL 未启动或 IP/端口错误 | 确认 `192.168.0.107:3306` 可达，检查 `ry_cloud` 配置 |
| `[MongoSink] 连接失败，降级到 JSONL` | MongoDB 未启动或端口错误 | 检查 `192.168.0.107:27018`，或将 `logging.mongo.enabled` 设为 `false` |
| `FileNotFoundError: env_xxx.yaml 不存在` | `TEST_ENV` 设置了不存在的环境名 | 确认文件名与 `TEST_ENV` 值一致，可用环境：`dev` / `test` |
| `AuthError: Token 失效` | `system_api.default_password` 与服务端不匹配 | 检查 `config/env_dev.yaml` 中 `system_api.default_password` |
| 接口返回 `401` / `未登录` | Token 未注入或已过期 | 确认用例调用了 `api.set_token(token)` 且 token 在有效期内 |
| `ConnectionError: 连接 system_api 失败` | RuoYi 服务未启动 | 确认 `http://192.168.0.107/dev-api` 可访问 |

针对 **100+ 接口**、**海量动态参数**以及**复杂业务闭环**的架构要求，目录结构的设计必须兼顾**模块化**与**搜索效率**。

以下是为您设计的工业级 Python-Pytest 接口自动化项目目录结构：

------

## 项目目录结构全景图

Plaintext

```
finance_api_automation/
├── api/                        # 第三层：原子接口定义层 (Atomic API)
│   ├── base_api.py             # 接口基类，封装通用调用逻辑
│   ├── account/                # 按业务模块分组
│   │   ├── register_api.py     # 开户模块接口定义
│   │   └── login_api.py
│   └── payment/
│       └── transfer_api.py     # 转账模块接口定义
├── business/                   # 第二层：业务流编排层 (Business Flow)
│   ├── account_flows.py        # 封装长链路逻辑（如：开户+授信+激活）
│   └── loan_flows.py           # 封装放款/还款链路
├── core/                       # 第四层：核心引擎层 (Core Engine)
│   ├── data_engine.py          # 核心：解析 YAML 标签、指令映射、渲染动态数据
│   ├── template_manager.py     # 核心：懒加载机制、LRU 缓存管理
│   ├── request_wrapper.py      # 核心：请求封装、自定义状态码 (9888x) 拦截处理
│   ├── context.py              # 全局上下文管理器 (GlobalContext)，单例模式
│   └── validator.py            # 断言引擎：支持 Schema 校验、JSONDiff、DB 校验
├── data/                       # 第五层：配置与数据资源层 (Data & Config)
│   ├── templates/              # 100+ 接口的 YAML 模板 (按模块分文件夹)
│   │   ├── account/
│   │   │   └── register.yaml   # 包含 40-90 个字段的生成规则
│   │   └── payment/
│   ├── common_dicts.yaml       # 公共字典池（金融枚举值）
│   └── schemas/                # JSON Schema 定义文件（用于契约断言）
├── tests/                      # 第一层：执行与用例层 (Test Case)
│   ├── conftest.py             # 全局 Fixture：DB 预检、环境初始化、Renderer 注入
│   ├── test_account/           # 账户模块用例
│   │   └── test_register.py
│   └── test_scenarios/         # 跨模块复杂场景测试用例
├── utils/                      # 公共工具类 (Common Utils)
│   ├── db_client.py            # 数据库连接池、健康检查、自动重连
│   ├── factory.py              # 业务工厂：三要素生成算法 (IdentityFactory)
│   └── logger.py               # 日志封装：支持请求/响应链路全记录
├── config/                     # 环境配置
│   ├── settings.py             # 配置加载逻辑
│   ├── env_dev.yaml            # 开发环境配置 (URL, DB 账户, Key)
│   └── env_test.yaml           # 测试环境配置
├── pytest.ini                  # Pytest 运行参数配置
├── requirements.txt            # 依赖包清单
└── run.py                      # 命令行启动入口 (可选)
```

------

## 核心目录职责详解

### 1. `core/` (框架大脑)

这是最体现技术方案的一层。

- **`template_manager.py`**：实现您要求的**懒加载**。它只在 `api/` 层调用时才去 `data/templates/` 读取对应的 YAML，并利用缓存避免重复 I/O。
- **`data_engine.py`**：处理 40-90 个字段的**随机化**。它负责把 YAML 里的 `${rand_str}` 变成真实的物理参数。
- **`request_wrapper.py`**：处理**自定义状态码**。它重写了请求响应拦截，确保 `98880` 等业务异常码不会被协议层直接抛错，而是传递给断言层。

### 2. `data/templates/` (数据画像)

这里存放那 **100+ 个 YAML 文件**。

- 为了防止一个文件夹下文件过多，必须按照**业务模块子目录**（如 `account/`, `payment/`）进行物理隔离。
- 每个 YAML 描述一个接口的“数据画像”，通过标签指定哪些是字典值、哪些是随机长度参数。

### 3. `api/` vs `business/` (原子与编排)

- **`api/`**：仅负责“怎么发请求”。比如 `RegisterApi` 类只知道它对应 `register.yaml`。
- **`business/`**：负责“怎么做业务”。它会调用多个 `api/` 下的方法，并将中间产生的 `apply_no` 存入 `GlobalContext`。

### 4. `utils/db_client.py` (环境监控)

- 负责**数据库健康检查**。在 `tests/conftest.py` 的 `session` 级别 fixture 中调用，确保 100+ 用例跑之前，数据库是连通的。

------

## 这种结构的优势

1. **极高可维护性**：如果 100 多个接口中有 1 个接口的字段变了，你只需要去 `data/templates/` 下改对应的 YAML，不需要动任何代码。
2. **清晰的搜索路径**：当测试报告显示 `api_user_reg` 接口报错时，你可以根据目录结构快速定位到 `api/account/register_api.py` 和 `data/templates/account/register.yaml`。
3. **性能最优化**：通过 `core/` 下的缓存和懒加载设计，即使有 1000 个 YAML，内存占用也能保持在极低水平。
4. **符合业务直觉**：金融业务的复杂性被 `business/` 层消化，`tests/` 层只剩下最纯净的业务断言。


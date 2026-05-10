# 模块映射

## 根目录

| 路径 | 职责 |
| --- | --- |
| `run.py` | 命令行测试入口，设置环境、marker、并发和报告打开。 |
| `pytest.ini` | Pytest 发现规则、默认参数、marker（smoke/regression/system/scenario/slow/data_seed）、日志配置、覆盖率配置。 |
| `requirements.txt` | Python 依赖。 |
| `SKILL.md` | 项目已有概要 skill。 |
| `finance_api_skill/` | 本次整理出的架构与业务流程 skill 资产。 |

## `config/`

| 文件 | 职责 |
| --- | --- |
| `settings.py` | `AppConfig` 单例配置加载器。 |
| `env_test.yaml` | 测试环境 API、system API、数据库、Allure、日志配置。 |
| `env_dev.yaml` | 开发环境配置。 |

使用规则：

- 不要在用例中硬编码 base_url、数据库连接或默认账号。
- 优先从 `cfg` 获取配置。
- 切换环境时通过 `TEST_ENV` 或 `python3 run.py --env`。

## `core/`

| 文件 | 关键对象 | 职责 |
| --- | --- | --- |
| `request_wrapper.py` | `RequestWrapper` | 统一 HTTP 请求、token、trace_id、重试、日志、响应错误分类。 |
| `data_engine.py` | `DataEngine` | 渲染 YAML 动态标签，应用 overrides，读取 `GlobalContext`。 |
| `template_manager.py` | `TemplateManager` | 懒加载 YAML 模板，LRU 缓存，返回深拷贝。 |
| `context.py` | `GlobalContext` | 线程安全的跨接口变量池。 |
| `validator.py` | `Validator` | 响应断言和结构校验辅助。 |
| `settings.py` | 路径常量 | 项目根目录、模板目录、输出目录等路径。 |

扩展建议：

- 新增动态标签时改 `DataEngine._dispatch()`。
- 新增响应错误分类时改 `RequestWrapper._handle_response()`。
- 新增全局输出目录时改 `core/settings.py`。

## `api/`

| 路径 | 职责 |
| --- | --- |
| `api/base_api.py` | API 基类，负责模板构建和 wrapper 注入。 |
| `api/system/base_system_api.py` | system 模块 API 基类，读取 `system_api` 配置。 |
| `api/system/login_api.py` | 登录接口。 |
| `api/system/user_api.py` | 用户管理接口。 |
| `api/system/role_api.py` | 角色管理、授权、数据权限接口。 |
| `api/system/post_api.py` | 岗位管理接口。 |
| `api/system/dept_api.py` | 部门管理接口。 |
| `api/system/notice_api.py` | 通知公告接口。 |

API 层规则：

- API 方法返回原始响应字典。
- API 层只做请求组装，不做复杂业务判断。
- 每次请求传 `_module`、`_api_name`、`_business_type`、`_service`，便于日志检索。

## `business/`

| 文件 | 职责 |
| --- | --- |
| `system_flows.py` | system 模块可复用业务编排，目前包含登录和获取用户信息链路。 |

业务层规则：

- 适合沉淀跨用例复用的链路。
- 负责上下文写入和 Allure 步骤组织。
- 不要把一次性测试场景过早抽成业务流，先在用例中验证稳定后再沉淀。

## `tests/`

| 路径 | 职责 |
| --- | --- |
| `tests/conftest.py` | 全局 fixture、API 日志生命周期、DB 健康检查、Allure 失败附件。 |
| `tests/test_system/conftest.py` | system 模块局部 fixture，获取 token，只检查 `ry_cloud`。 |
| `tests/test_system/test_user_login.py` | 登录相关测试。 |
| `tests/test_system/test_add_user.py` | 新增用户测试。 |
| `tests/test_system/test_update_user.py` | 修改用户测试。 |
| `tests/test_system/test_delete_user.py` | 删除用户测试。 |
| `tests/test_system/test_role_crud.py` | 角色 CRUD。 |
| `tests/test_system/test_role_list.py` | 角色列表。 |
| `tests/test_system/test_role_auth_users.py` | 角色授权用户。 |
| `tests/test_system/test_role_data_scope_status.py` | 角色数据权限和状态。 |
| `tests/test_system/test_post_crud.py` | 岗位 CRUD。 |
| `tests/test_system/test_post_list.py` | 岗位列表。 |
| `tests/test_system/test_dept_crud.py` | 部门 CRUD。 |
| `tests/test_system/test_dept_list.py` | 部门列表。 |
| `tests/test_system/test_notice_crud.py` | 公告 CRUD。 |
| `tests/test_system/test_notice_list.py` | 公告列表。 |
| `tests/test_system/test_permission_rbac.py` | 权限/RBAC 回归。 |
| `tests/test_system/test_user_post_role_business_flow.py` | 用户、岗位、角色组合业务流。 |
| `tests/test_system/test_system_business_flows.py` | BIZ-001~010 端到端业务流。 |

测试层规则：

- 使用 `try/finally` 清理测试数据。
- 用 UUID 生成唯一实体名，避免并发和重复执行污染。
- 关键响应和 DB 回查用 Allure 附件记录。
- 涉及写接口时必须考虑数据清理和关联表残留。

## `utils/`

| 文件 | 职责 |
| --- | --- |
| `db_client.py` | 数据库注册、连接、健康检查、查询。 |
| `api_logger.py` | API 结构化日志、MongoSink、JsonlSink、脱敏。 |
| `logger.py` | 项目日志封装。 |
| `system_ruoyi_queries.py` | RuoYi system 模块常用 DB 查询和清理辅助。 |

使用规则：

- DB 查询优先复用 `system_ruoyi_queries.py`。
- 新增常用 SQL 辅助时放到 `utils/`，不要散落在多个测试文件。
- 清理残留绑定时优先复用已有 purge 函数。

## `data/`

| 路径 | 职责 |
| --- | --- |
| `data/templates/` | 请求模板。 |
| `data/schemas/` | JSON schema 或结构校验文件。 |

模板规则：

- 根节点通常包含 `payload`。
- 用例层覆盖字段使用点分路径，例如 `payload.userName`。
- 动态字段优先用 `DataEngine` 标签。

## `outputs/` 和 `report/`

| 路径 | 职责 |
| --- | --- |
| `outputs/allure_results/` | Allure 原始结果。 |
| `outputs/coverage_html/` | HTML 覆盖率。 |
| `outputs/logs/` | Pytest 和项目日志。 |
| `outputs/api_logs/` | API 日志 JSONL 降级目录。 |
| `report/` | Allure HTML 报告输出目录。 |

注意：

- 这些目录多为运行产物，不应作为业务代码依赖。
- 排障时可读取，但不要在业务逻辑中硬编码依赖产物路径。

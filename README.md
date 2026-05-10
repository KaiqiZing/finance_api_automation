# finance_api_automation

基于 **Python + Pytest + Requests** 的接口自动化工程，当前主要覆盖 **RuoYi 若依** 后端 **system** 模块（用户、角色、岗位、部门、通知公告等），并预留金融业务扩展能力。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 分层架构 | 用例（`tests`）→ 业务流（`business`）→ 原子接口（`api`）→ 核心引擎（`core`）→ 数据与模板（`data`） |
| 配置驱动 | `config/env_dev.yaml`、`config/env_test.yaml` 切换环境与 API / DB 等参数 |
| 模板与动态数据 | YAML 模板 + `DataEngine` 标签（如 `${get_mobile}`、`$CONTEXT{key}`）减少硬编码 |
| 全局上下文 | `GlobalContext` 支撑长链路跨接口传参 |
| 契约与断言 | `jsonschema`、`deepdiff`、`Validator` 等组合校验 |
| 报告与覆盖率 | Allure、`pytest-cov` HTML、控制台与文件日志 |
| CI | 根目录 `Jenkinsfile`：参数化环境 / 标签 / 并发、Allure、pytest-html 独立报告、产物归档与通知 |

更细的架构与排障说明见仓库内文档（见文末「延伸阅读」）。

---

## 环境要求

- **Python**：建议 **3.11+**（与 `requirements.txt` 中版本约束一致即可）。
- **操作系统**：macOS / Linux / Windows（路径统一用 `pathlib`）。
- **可选**：[Allure Commandline](https://docs.qameta.io/allure/)，用于本地 `run.py --report` 或手动 `allure generate/open`。
- **数据库**：`tests/conftest.py` 会在会话级对配置中的数据源做健康检查；若库不可达，用例收集/执行会失败。本地无库时需自行调整 fixture（仅限开发自测，勿提交关闭检查的代码到主干）。

---

## 快速开始

```bash
git clone <你的仓库地址>
cd finance_api_automation

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 配置

1. 复制或编辑 `config/env_test.yaml` / `config/env_dev.yaml`，填入可连通的 **base_url**、**鉴权**、**数据库** 等（勿将真实密码提交到公开仓库）。
2. 运行时通过环境变量 **`TEST_ENV`** 选择环境，取值为 `test` 或 `dev`，对应加载 `env_{TEST_ENV}.yaml`。未设置时默认为 `test`（见 `config/settings.py` 中 `AppConfig`）。

---

## 运行测试

### 推荐入口：`run.py`

```bash
python3 run.py                         # 默认 test 环境，跑 tests 下全部用例
python3 run.py --env dev               # 使用 dev 配置
python3 run.py --mark smoke            # 仅 @pytest.mark.smoke
python3 run.py --mark regression -n 4  # 回归标签，4 进程并行（pytest-xdist）
python3 run.py --failfast              # 首个失败即停止（-x）
python3 run.py --report                # 结束后生成并打开 Allure（需本机已安装 allure 命令）
```

### 直接使用 pytest

```bash
export TEST_ENV=test    # 或 dev
pytest
pytest tests/test_system/test_user_login.py -v
pytest -m "smoke and not slow" -n 2
```

### Pytest 标记（`pytest.ini`）

| 标记 | 含义 |
|------|------|
| `smoke` | 冒烟 |
| `regression` | 回归 |
| `account` / `payment` | 按业务模块筛选 |
| `scenario` | 跨模块场景 |
| `slow` | 耗时较长 |

---

## 输出目录说明

执行后常见产物路径（部分由 `pytest.ini` 固定）：

| 路径 | 内容 |
|------|------|
| `outputs/allure_results/` | Allure 原始数据（`--clean-alluredir` 每次会清空再写） |
| `outputs/coverage_html/` | 覆盖率 HTML（`api`、`business`、`core`） |
| `outputs/logs/pytest.log` | Pytest 文件日志（DEBUG） |
| `report/` | 可选：配合 `run.py --report` 时 Allure `generate` 的输出目录 |

在 **Jenkins** 流水线中，还会安装 `pytest-html` 并生成 **`outputs/extent_report/report.html`**（自包含单文件），便于在构建页「ExtentReport」中浏览；详见 `Jenkinsfile`。

---

## 仓库目录结构（摘要）

```text
finance_api_automation/
├── api/                 # 原子 HTTP 封装（含 system 子模块）
├── business/            # 跨接口业务编排（如 system_flows）
├── config/              # env_*.yaml、AppConfig 加载
├── core/                # RequestWrapper、TemplateManager、DataEngine、Validator、Context 等
├── data/                # YAML 模板、JSON Schema、公共字典
├── tests/               # 用例与 conftest（含 test_system 等）
├── utils/               # DB、日志等辅助
├── outputs/             # 运行生成物（建议 .gitignore）
├── docs/                # 项目使用说明与专题文档
├── finance_api_skill/   # 知识库：架构、环境、用例风格、脚本等
├── run.py               # CLI 入口
├── pytest.ini
├── requirements.txt
├── Jenkinsfile
└── README.md
```

---

## Jenkins 持续集成

根目录 **`Jenkinsfile`** 提供 Declarative Pipeline，支持：

- 参数：`TEST_ENV`、`TEST_MARK`、`WORKERS`（xdist）、`FAILFAST`
- 虚拟环境中安装 `requirements.txt` 与 **pytest-html**
- Allure 生成与发布（需 Jenkins **Allure** 插件）、Coverage 与 Extent 类 HTML 发布（需 **HTML Publisher** 等）
- 产物归档与邮件通知（需对应插件；收件人与钉钉等请按团队规范在流水线中配置）

首次接入时请根据实际 Agent 修改 `agent`、凭据与通知方式。

---

## 扩展与规范

- **新增接口**：在 `data/templates/<模块>/` 增加 YAML，在 `api/` 增加类并走 `_build_payload` + `RequestWrapper`。
- **新增用例**：命名符合 `test_*.py` / `test_*`，结合 `@pytest.mark` 与 Allure 注解分层。
- **动态标签扩展**：在 `core/data_engine.py` 中按需注册。

详细步骤、常见问题与模板字段约定见 **`docs/项目使用说明.md`**。

---

## 延伸阅读

| 文档 | 说明 |
|------|------|
| [docs/项目使用说明.md](docs/项目使用说明.md) | 安装、配置、运行、Allure、目录、扩展与 FAQ |
| [finance_api_skill/README.md](finance_api_skill/README.md) | 知识库索引与脚本入口 |
| [finance_api_skill/docs/tech_architecture.md](finance_api_skill/docs/tech_architecture.md) | 技术架构与数据流 |
| [finance_api_skill/docs/environments.md](finance_api_skill/docs/environments.md) | dev/test 配置项说明与切换 |
| [finance_api_skill/docs/test_case_style.md](finance_api_skill/docs/test_case_style.md) | 用例与 Allure 书写风格 |

---

## 许可证与贡献

若仓库根目录未包含 `LICENSE`，请以团队或公司策略为准。提交代码前建议本地执行目标标签或全量用例，并确保敏感信息仅通过密钥或私有配置注入，不进入版本库。

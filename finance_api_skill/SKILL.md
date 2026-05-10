---
name: finance-api-automation
description: 整理和使用 finance_api_automation 项目的技术架构、接口自动化规范、RuoYi system 业务流程、Pytest/Allure/Requests/Mongo 日志链路。Use when analyzing this repository, writing API automation tests, extending system module flows, debugging trace_id logs, or onboarding engineers to this project.
---

# Finance API Automation

## 使用场景

当用户提到以下任务时，优先使用本 skill：

- 理解 `finance_api_automation` 项目的技术架构、目录职责、调用链路。
- 新增或维护 Pytest + Requests + Allure 接口自动化用例。
- 扩展 RuoYi system 模块接口，包括用户、角色、岗位、部门、公告。
- 排查接口失败、DB 断言失败、Allure 附件、Mongo/JSONL API 日志。
- 梳理业务流程、测试策略、模块边界或新成员交接文档。

## 快速工作流

1. 先阅读 [docs/tech_architecture.md](docs/tech_architecture.md)，确认项目分层与核心链路。
2. 涉及 system 模块业务时，阅读 [docs/business_flows.md](docs/business_flows.md)。
3. 需要定位文件职责时，阅读 [docs/module_map.md](docs/module_map.md)。
4. 需要生成相似代码时，阅读 [docs/code_generation_templates.md](docs/code_generation_templates.md)。
5. 需要快速巡检项目关键文件时，执行：

```bash
python3 finance_api_skill/scripts/project_snapshot.py
```

6. 需要运行 system 业务流冒烟时，执行：

```bash
bash finance_api_skill/scripts/flow_smoke_runner.sh
```

## 项目约定

- 原子接口只放在 `api/`，不写业务断言。
- 多接口业务编排放在 `business/` 或 `tests/test_system/test_system_business_flows.py`。
- 请求统一经过 `core/request_wrapper.py`，不要绕过 `RequestWrapper` 直接调用 `requests`。
- 测试数据优先通过 YAML 模板和 `DataEngine` 生成，用例层通过 overrides 覆盖字段。
- 跨接口变量使用 `GlobalContext`，用例结束后由 fixture 自动清理。
- system 模块只依赖 `ry_cloud` 数据库，局部 fixture 会覆盖全局 DB 健康检查。
- 新增失败排查能力时，优先补充 Allure 附件和 `trace_id` 日志，而不是只打印日志。

## 输出要求

- 给出方案时优先引用真实文件路径。
- 写测试建议时包含前置数据、接口步骤、DB 校验、清理策略。
- 排查失败时按 `接口响应 -> trace_id -> Allure 附件 -> DB 回查 -> 清理残留` 的顺序分析。
- 不要把环境密码、token、身份证、银行卡、手机号等敏感字段明文写入文档或日志。

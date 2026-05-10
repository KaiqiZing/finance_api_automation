# finance_api_skill

`finance_api_skill` 是当前 `finance_api_automation` 项目的知识资产目录，用于沉淀技术架构、业务流程、模块职责、排障路径和常用脚本。

## 目录

```text
finance_api_skill/
  SKILL.md
  README.md
  docs/
    tech_architecture.md
    business_flows.md
    module_map.md
    code_generation_templates.md
    test_case_style.md
    logging_architecture.md
    environments.md
  scripts/
    project_snapshot.py
    flow_smoke_runner.sh
  examples/
    skill_usage_examples.md
```

## 内容说明

- `SKILL.md`：Cursor Agent 可读取的主 skill，包含触发场景、工作流和项目约定。
- `docs/tech_architecture.md`：项目技术架构、核心链路、运行机制、完整数据流图。
- `docs/business_flows.md`：system 模块业务流程和 BIZ-001~010 场景整理。
- `docs/module_map.md`：目录职责、关键文件、扩展位置。
- `docs/code_generation_templates.md`：API 类、YAML 模板、CRUD 用例、业务流用例、DB 查询辅助函数的代码生成模板。
- `docs/test_case_style.md`：测试用例格式与 @allure 注解风格规范（基于 test_system 真实用例整理）。
- `docs/logging_architecture.md`：项目日志设计架构详细说明（loguru 运行时日志 + ApiLogger 结构化日志双层体系）。
- `docs/environments.md`：dev / test 两套环境的完整配置说明、差异对比、切换方式、DB 连接和常见问题排查。
- `scripts/project_snapshot.py`：检查项目关键文件是否存在并输出结构快照。
- `scripts/flow_smoke_runner.sh`：运行 system 业务流冒烟测试的示例脚本。
- `examples/skill_usage_examples.md`：常见使用方式和提问模板。

## 快速使用

```bash
python3 finance_api_skill/scripts/project_snapshot.py
bash finance_api_skill/scripts/flow_smoke_runner.sh
```

运行前请确认测试环境、数据库和 Allure 依赖已准备好。

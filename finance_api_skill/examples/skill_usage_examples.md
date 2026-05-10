# 使用示例

## 让 Agent 理解项目

可以这样提问：

```text
基于 finance_api_skill，解释当前项目的接口自动化架构。
```

```text
基于 finance_api_skill，梳理 system 模块用户、角色、岗位之间的业务关系。
```

```text
基于 finance_api_skill，告诉我新增一个 system 接口用例应该改哪些文件。
```

## 快速巡检关键文件

```bash
python3 finance_api_skill/scripts/project_snapshot.py
```

期望输出：

```text
=== finance_api_automation project snapshot ===
[OK  ] run.py
[OK  ] pytest.ini
...
all key files exist.
```

## 运行 system 业务流冒烟

```bash
bash finance_api_skill/scripts/flow_smoke_runner.sh
```

等价于：

```bash
python3 run.py --env test --mark scenario -n 1
```

## 新增接口用例时的提问模板

```text
我要给 system 模块新增一个【资源名称】接口测试。
请基于 finance_api_skill 给出：
1. 应该新增或修改哪些文件
2. API 方法应该放在哪里
3. 是否需要 YAML 模板
4. 用例应该如何做 DB 校验和清理
```

## 排查失败时的提问模板

```text
这个 system 业务流失败了。
请基于 finance_api_skill，按接口响应、trace_id、Allure 附件、DB 回查、残留清理的顺序帮我分析。
```

## 文档维护建议

当项目发生以下变化时，建议同步更新本目录：

- 新增 system 资源接口。
- 新增业务流文件或 BIZ 场景。
- 修改 `RequestWrapper` 的错误分类或日志字段。
- 修改 `DataEngine` 动态标签。
- 修改 `tests/conftest.py` 中的 fixture、hook 或 Allure 附件策略。

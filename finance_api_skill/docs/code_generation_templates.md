# 代码生成模板

本文档用于指导大模型按当前项目风格生成相似代码。生成代码前，应先确认目标资源属于哪个模块、是否需要 YAML 模板、是否需要 DB 回查、是否需要清理测试数据。

## 总体生成顺序

新增一个 system 资源接口自动化能力时，按以下顺序生成：

1. `data/templates/system/*.yaml`：POST/PUT 请求体模板。
2. `api/system/*_api.py`：原子接口封装。
3. `utils/system_ruoyi_queries.py`：必要的 DB 查询和清理辅助。
4. `tests/test_system/test_*_crud.py`：单资源 CRUD 用例。
5. `tests/test_system/test_system_business_flows.py` 或独立业务流文件：跨资源端到端链路。

## 命名规范

- API 类名：`System{Resource}API`，例如 `SystemNoticeAPI`。
- API 文件名：`{resource}_api.py`，例如 `notice_api.py`。
- 测试类名：`Test{Resource}Crud` 或 `Test{Resource}BusinessFlow`。
- 测试文件名：`test_{resource}_crud.py` 或 `test_{resource}_business_flow.py`。
- Python 参数使用 snake_case，例如 `notice_title`、`role_id`、`post_code`。
- RuoYi 请求字段使用 camelCase，例如 `noticeTitle`、`roleId`、`postCode`。
- overrides 使用点分路径，例如 `payload.noticeTitle`。
- `_business_type` 使用 `system:{resource}:{action}`，例如 `system:notice:add`。

## API 类模板

适用位置：`api/system/{resource}_api.py`

```python
"""
System{Resource}API：系统{资源中文名}相关接口（RuoYi 后端）。

接口列表:
    GET    /system/{resource}/list          获取列表
    POST   /system/{resource}               新增
    PUT    /system/{resource}               修改
    GET    /system/{resource}/{id}          获取详情
    DELETE /system/{resource}/{ids}         删除

模板目录: data/templates/system/
依赖: Authorization: Bearer <token>（通过 set_token() 注入）
"""
from __future__ import annotations

from typing import Any

from api.system.base_system_api import SystemBaseAPI


class System{Resource}API(SystemBaseAPI):
    """系统{资源中文名}接口，需先注入 Token 才能请求。"""

    _MODULE = "system"

    def list_{resources}(
        self,
        name: str | None = None,
        status: str | None = None,
        page_num: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """获取{资源中文名}列表（支持筛选与分页）。"""
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if status is not None:
            params["status"] = status
        if page_num is not None:
            params["pageNum"] = page_num
        if page_size is not None:
            params["pageSize"] = page_size
        return self._wrapper.get(
            "/system/{resource}/list",
            params=params or None,
            _module="system",
            _api_name="list_{resources}",
            _business_type="system:{resource}:list",
            _service="ruoyi",
        )

    def add_{resource}(self, name: str | None = None, status: str | None = None) -> dict[str, Any]:
        """新增{资源中文名}。"""
        overrides: dict[str, Any] = {}
        if name is not None:
            overrides["payload.name"] = name
        if status is not None:
            overrides["payload.status"] = status

        payload = self._build_payload(self._MODULE, "add_{resource}", overrides or None)
        return self._wrapper.post(
            "/system/{resource}",
            json=payload,
            _module="system",
            _api_name="add_{resource}",
            _business_type="system:{resource}:add",
            _service="ruoyi",
        )

    def update_{resource}(self, {resource}_id: int, name: str | None = None, status: str | None = None) -> dict[str, Any]:
        """修改{资源中文名}。"""
        overrides: dict[str, Any] = {"payload.{resource}Id": {resource}_id}
        if name is not None:
            overrides["payload.name"] = name
        if status is not None:
            overrides["payload.status"] = status

        payload = self._build_payload(self._MODULE, "update_{resource}", overrides)
        return self._wrapper.put(
            "/system/{resource}",
            json=payload,
            _module="system",
            _api_name="update_{resource}",
            _business_type="system:{resource}:edit",
            _service="ruoyi",
        )

    def get_{resource}(self, {resource}_id: int) -> dict[str, Any]:
        """获取{资源中文名}详情。"""
        return self._wrapper.get(
            f"/system/{resource}/{{{resource}_id}}",
            _module="system",
            _api_name="get_{resource}",
            _business_type="system:{resource}:query",
            _service="ruoyi",
        )

    def delete_{resources}(self, {resource}_ids: list[int]) -> dict[str, Any]:
        """删除{资源中文名}（支持批量，路径参数逗号分隔）。"""
        ids_str = ",".join(str(item_id) for item_id in {resource}_ids)
        return self._wrapper.delete(
            f"/system/{resource}/{{ids_str}}",
            _module="system",
            _api_name="delete_{resources}",
            _business_type="system:{resource}:remove",
            _service="ruoyi",
        )
```

生成注意：

- 真实 RuoYi 字段要替换模板中的 `name`、`{resource}Id`。
- 如果接口无请求体，不要强行创建 YAML 模板。
- 路径参数批量删除一般使用逗号拼接。
- API 方法不要写 `assert`，断言放到测试层。

## YAML 请求模板

适用位置：`data/templates/system/add_{resource}.yaml`

```yaml
payload:
  name: "${rand_str(chn, 6)}"
  status: "0"
  remark: "自动化测试_${uuid}"
```

适用位置：`data/templates/system/update_{resource}.yaml`

```yaml
payload:
  resourceId: null
  name: "${rand_str(chn, 6)}"
  status: "0"
  remark: "自动化修改_${uuid}"
```

生成注意：

- 根节点优先使用 `payload`。
- 必填 ID 字段在 update 模板中可设为 `null`，由用例或 API 方法 overrides 覆盖。
- 唯一字段优先使用 `${uuid}` 或用例中的 `_gen_xxx()`。
- 不要在 YAML 中写真实密码、token、手机号、身份证、银行卡。

## DB 查询辅助模板

适用位置：`utils/system_ruoyi_queries.py`

```python
def fetch_{resource}_id_by_{field}({field}: str) -> int | None:
    """
    按 {field} 精确查询{资源中文名} ID（用于新增后清理或断言）。

    Returns:
        {resource}_id（int），若未找到则返回 None；多条时取最近插入的一条。
    """
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT {resource}_id FROM sys_{resource} "
        "WHERE {db_field} = %s "
        "ORDER BY {resource}_id DESC LIMIT 1",
        ({field},),
    )
    if row is None:
        logger.warning("[system_ruoyi_queries] sys_{resource} 中未找到 {db_field}={}", {field})
        return None
    {resource}_id = int(row["{resource}_id"])
    logger.debug("[system_ruoyi_queries] {db_field}={} -> {resource}_id={}", {field}, {resource}_id)
    return {resource}_id
```

生成注意：

- system 模块 DB 固定使用 `DBClient.instance("ry_cloud")`。
- 查询条件要符合 RuoYi 表字段，例如 `del_flag='0'`、`status='0'`。
- 新增后接口不返回 ID 时，必须提供 DB 回查函数。
- 清理关联表时要提供明确的 purge 函数，且只删除测试对象相关数据。

## CRUD 测试模板

适用位置：`tests/test_system/test_{resource}_crud.py`

```python
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.{resource}_api import System{Resource}API
from tests.test_system.conftest import _login_and_get_token
from utils.system_ruoyi_queries import fetch_{resource}_id_by_{field}


def _gen_{resource}_name() -> str:
    return "自动化{资源中文名}_" + uuid.uuid4().hex[:10]


@allure.epic("系统管理模块")
@allure.feature("{资源中文名}")
class Test{Resource}Crud:
    """{资源中文名} CRUD 综合测试。"""

    @allure.story("新增{资源中文名}")
    @allure.title("TC-SYS-{CODE}-001：仅必填字段新增成功")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_add_{resource}_required_only(self) -> None:
        token = _login_and_get_token()
        api = System{Resource}API()
        api.set_token(token)
        name = _gen_{resource}_name()

        try:
            with allure.step("新增{资源中文名}"):
                resp = api.add_{resource}(name=name, status="0")
            allure.attach(str(resp), name="Add{Resource} Response", attachment_type=allure.attachment_type.TEXT)
            assert resp.get("code") == 200, f"新增失败: {resp}"

            {resource}_id = fetch_{resource}_id_by_{field}(name)
            assert {resource}_id is not None, "新增后 DB 未查到 ID"
        finally:
            {resource}_id = fetch_{resource}_id_by_{field}(name)
            if {resource}_id is not None:
                api.set_token(token)
                api.delete_{resources}([{resource}_id])

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-{CODE}-002：未携带 Token 新增，断言被拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_{resource}_without_token(self) -> None:
        api = System{Resource}API()
        resp = api.add_{resource}(name=_gen_{resource}_name(), status="0")
        allure.attach(str(resp), name="NoToken Add", attachment_type=allure.attachment_type.TEXT)
        assert resp.get("code") != 200, resp
```

生成注意：

- 登录优先复用 `tests.test_system.conftest._login_and_get_token`。
- 用例中创建的实体必须用 `try/finally` 清理。
- 新增、修改、删除后尽量通过 DB 或详情接口校验最终态。
- 无 Token 场景不要调用 `set_token()`。
- `pytest.skip()` 仅用于环境前置数据缺失，不要掩盖真实失败。

## 业务流用例模板

适用位置：`tests/test_system/test_system_business_flows.py` 或新建业务流测试文件。

```python
@allure.story("{业务域}")
@allure.title("TC-SYS-BIZ-XXX：{业务流名称}")
@allure.severity(allure.severity_level.NORMAL)
def test_biz_xxx_{flow_name}(self) -> None:
    """
    链路: 步骤1 -> 步骤2 -> 步骤3 -> 清理
    关键断言: 描述最终态和 DB 字段。
    """
    token = _login_and_get_token()
    user_api, role_api, post_api, dept_api, notice_api = _setup_apis(token)

    created_id: int | None = None
    related_id: int | None = None

    try:
        with allure.step("准备前置数据"):
            ...

        with allure.step("执行业务动作"):
            ...

        with allure.step("DB 校验最终态"):
            row = DBClient.instance("ry_cloud").fetch_one(
                "SELECT ... FROM ... WHERE ... = %s LIMIT 1",
                (created_id,),
            )
            _attach_json("DB回查", row)
            assert row is not None

    finally:
        # 逆序清理，先删依赖方，再删被依赖方。
        ...
```

生成注意：

- 每个业务流先写清楚链路和关键断言。
- 变量命名要表达实体类型，例如 `user_id`、`role_id`、`post_id`、`dept_id`。
- 清理顺序遵循依赖关系：用户优先，关联资源其次，父级资源最后。
- 对预期失败的业务约束，用例标题和 step 中要写明“预期失败”。

## Allure 附件模板

```python
import json
from typing import Any

import allure


def _attach_json(name: str, data: Any) -> None:
    allure.attach(
        body=json.dumps(data, ensure_ascii=False, indent=2, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )
```

使用建议：

- 响应体、DB 回查、关联表计数用 JSON 附件。
- token、密码、手机号、身份证、银行卡不要明文附加。
- 失败排查需要能看到“入参摘要、响应摘要、DB 最终态”。

## 生成前检查清单

- 是否已有同类 API 类可模仿。
- 是否已有 YAML 模板可复用。
- 新增接口是否需要 token。
- 成功响应是否返回 ID；不返回 ID 时是否已有 DB 回查函数。
- 是否涉及唯一字段；唯一字段是否使用 UUID。
- 是否涉及关联表；是否需要 purge 清理函数。
- 是否能通过详情接口或 DB 校验最终态。
- 是否需要 Allure step 和附件。
- 是否需要无 Token、重复数据、删除不存在 ID 等异常场景。

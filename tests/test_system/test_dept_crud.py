"""
系统部门 CRUD 测试用例。

真实接口:
    POST   http://192.168.0.107/dev-api/system/dept         新增部门
    GET    http://192.168.0.107/dev-api/system/dept/{id}    获取部门详情
    PUT    http://192.168.0.107/dev-api/system/dept         修改部门
    DELETE http://192.168.0.107/dev-api/system/dept/{id}    删除部门

    注意: POST 响应不返回 deptId，须通过 DB 查询（fetch_dept_id_by_dept_name）回取。

用例清单:
    TC-SYS-DPT-010  仅必填字段新增部门，断言 code==200
    TC-SYS-DPT-011  含可选字段 leader/phone/email 新增部门，断言 code==200
    TC-SYS-DPT-012  重复 deptName 在同一父部门下新增，断言 code==500
    TC-SYS-DPT-013  未携带 Token 新增部门，断言被鉴权拦截
    TC-SYS-DPT-014  获取部门详情（新增后按 deptId 查询），断言 code==200 且字段匹配
    TC-SYS-DPT-015  修改部门（完整正向链路：新增→查详情→修改→再查），断言 code==200
    TC-SYS-DPT-016  新增后删除，断言 code==200
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.dept_api import SystemDeptAPI
from api.system.login_api import SystemLoginAPI
from utils.system_ruoyi_queries import fetch_dept_id_by_dept_name

# 若依系统根部门 ID（用作测试部门的父节点，不干扰正式树结构）
ROOT_DEPT_ID = 100


# ==============================================================================
# 辅助函数
# ==============================================================================

def _gen_dept_name() -> str:
    """生成唯一部门名称（取 UUID 前 6 位），防止用例间冲突。"""
    return "测试部门_" + uuid.uuid4().hex[:6]


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


def _create_test_dept(
    dept_api: SystemDeptAPI,
    parent_id: int = ROOT_DEPT_ID,
    order_num: int = 999,
) -> tuple[str, int | None]:
    """
    新增一个测试部门，返回 (dept_name, dept_id)。
    dept_id 通过 DB 回查；回查失败时为 None（调用方需处理）。
    调用方负责在测试结束后通过接口删除该部门。
    """
    dept_name = _gen_dept_name()
    resp = dept_api.add_dept(
        parent_id=parent_id,
        dept_name=dept_name,
        order_num=order_num,
    )
    assert resp.get("code") == 200, f"前置新增部门失败: {resp}"
    dept_id = fetch_dept_id_by_dept_name(dept_name, parent_id)
    return dept_name, dept_id


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("部门管理")
class TestDeptCrud:
    """部门 CRUD 接口综合测试集合。"""

    # ==================================================================
    # TC-SYS-DPT-010：仅必填字段新增
    # ==================================================================

    @allure.story("新增部门")
    @allure.title("TC-SYS-DPT-010：仅传必填字段（parentId/deptName/orderNum）新增部门成功")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_add_dept_required_fields_only(self) -> None:
        """
        只传三个必填字段，断言:
        - 响应 code == 200
        - 响应 msg == "操作成功"

        测试后通过接口删除所建部门，保持环境整洁。
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        dept_name = _gen_dept_name()

        with allure.step(f"调用新增接口（仅必填字段）: parentId={ROOT_DEPT_ID}, deptName={dept_name}"):
            resp = dept_api.add_dept(
                parent_id=ROOT_DEPT_ID,
                dept_name=dept_name,
                order_num=999,
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddDept Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 msg == '操作成功'"):
            assert resp.get("msg") == "操作成功", (
                f"msg 异常: {resp.get('msg')!r}"
            )

        with allure.step("清理：删除刚新增的测试部门"):
            dept_id = fetch_dept_id_by_dept_name(dept_name, ROOT_DEPT_ID)
            if dept_id is not None:
                dept_api.delete_dept(dept_id)

    # ==================================================================
    # TC-SYS-DPT-011：含可选字段新增
    # ==================================================================

    @allure.story("新增部门")
    @allure.title("TC-SYS-DPT-011：含可选字段 leader/phone/email 新增部门，断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_dept_with_optional_fields(self) -> None:
        """
        传入必填字段 + leader/phone/email，断言:
        - 响应 code == 200

        测试后通过接口删除所建部门。
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        dept_name = _gen_dept_name()

        with allure.step(f"调用新增接口（含可选字段）: deptName={dept_name}"):
            resp = dept_api.add_dept(
                parent_id=ROOT_DEPT_ID,
                dept_name=dept_name,
                order_num=998,
                leader="测试负责人",
                phone="13800138000",
                email="test@example.com",
                status="0",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddDept Optional Fields Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("清理：删除刚新增的测试部门"):
            dept_id = fetch_dept_id_by_dept_name(dept_name, ROOT_DEPT_ID)
            if dept_id is not None:
                dept_api.delete_dept(dept_id)

    # ==================================================================
    # TC-SYS-DPT-012：重复 deptName 在同一父部门下新增（负面）
    # ==================================================================

    @allure.story("新增部门")
    @allure.title("TC-SYS-DPT-012：同一父部门下重复 deptName 新增，断言 code==500")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_dept_duplicate_name(self) -> None:
        """
        同一父部门下两次使用相同 deptName 新增，断言:
        - 第一次 code == 200
        - 第二次 code == 500（部门名称重复）
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        dept_name = _gen_dept_name()

        with allure.step(f"第一次新增部门: deptName={dept_name}"):
            resp1 = dept_api.add_dept(
                parent_id=ROOT_DEPT_ID,
                dept_name=dept_name,
                order_num=999,
            )
        assert resp1.get("code") == 200, f"第一次新增失败: {resp1}"

        with allure.step(f"第二次新增（相同 deptName）: deptName={dept_name}"):
            resp2 = dept_api.add_dept(
                parent_id=ROOT_DEPT_ID,
                dept_name=dept_name,
                order_num=999,
            )

        with allure.step("附加第二次响应"):
            allure.attach(
                body=str(resp2),
                name="Duplicate DeptName Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言第二次 code == 500"):
            assert resp2.get("code") == 500, (
                f"期望 code==500，实际 code={resp2.get('code')}, msg={resp2.get('msg')}"
            )

        with allure.step("清理：删除第一次新增的测试部门"):
            dept_id = fetch_dept_id_by_dept_name(dept_name, ROOT_DEPT_ID)
            if dept_id is not None:
                dept_api.delete_dept(dept_id)

    # ==================================================================
    # TC-SYS-DPT-013：未携带 Token 新增部门
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-DPT-013：未携带 Token 新增部门，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_dept_without_token(self) -> None:
        """
        不注入 Token 直接调用新增接口，断言:
        - 响应 code != 200（通常为 401）
        """
        dept_api = SystemDeptAPI()

        with allure.step("不注入 Token，调用新增部门接口"):
            resp = dept_api.add_dept(
                parent_id=ROOT_DEPT_ID,
                dept_name=_gen_dept_name(),
                order_num=999,
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token AddDept Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

    # ==================================================================
    # TC-SYS-DPT-014：获取部门详情
    # ==================================================================

    @allure.story("获取部门详情")
    @allure.title("TC-SYS-DPT-014：新增部门后获取详情，断言 code==200 且关键字段匹配")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_dept_detail(self) -> None:
        """
        完整链路：新增部门 → DB 回查 deptId → 调用详情接口，断言:
        - 响应 code == 200
        - data.deptName 与新增时一致
        - data.parentId 与新增时一致
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        dept_name, dept_id = _create_test_dept(dept_api)

        if dept_id is None:
            pytest.skip(f"DB 中未找到 deptName={dept_name}，跳过详情测试")

        allure.attach(
            body=f"dept_id={dept_id}\ndept_name={dept_name}\nparent_id={ROOT_DEPT_ID}",
            name="新增部门信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        try:
            with allure.step(f"调用详情接口: GET /system/dept/{dept_id}"):
                resp = dept_api.get_dept(dept_id)

            with allure.step("附加详情响应"):
                allure.attach(
                    body=str(resp),
                    name="GetDept Response",
                    attachment_type=allure.attachment_type.TEXT,
                )

            with allure.step("断言 code == 200"):
                assert resp.get("code") == 200, (
                    f"获取详情失败: code={resp.get('code')}, msg={resp.get('msg')}"
                )

            with allure.step("断言详情中 deptName 与 parentId 与新增时一致"):
                data = resp.get("data", {})
                assert data.get("deptName") == dept_name, (
                    f"deptName 不匹配: 期望 {dept_name!r}，实际 {data.get('deptName')!r}"
                )
                assert data.get("parentId") == ROOT_DEPT_ID, (
                    f"parentId 不匹配: 期望 {ROOT_DEPT_ID}，实际 {data.get('parentId')}"
                )
        finally:
            with allure.step("清理：删除测试部门"):
                dept_api.delete_dept(dept_id)

    # ==================================================================
    # TC-SYS-DPT-015：修改部门
    # ==================================================================

    @allure.story("修改部门")
    @allure.title("TC-SYS-DPT-015：新增→查详情→修改→再查部门，断言 code==200 且修改后字段生效")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_dept(self) -> None:
        """
        完整正向链路：
        1. 新增测试部门；
        2. DB 回查 dept_id；
        3. 修改 deptName 与 orderNum，断言 code==200；
        4. 再次查详情确认修改生效。
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        dept_name, dept_id = _create_test_dept(dept_api)

        if dept_id is None:
            pytest.skip(f"DB 中未找到 deptName={dept_name}，跳过修改测试")

        new_dept_name = _gen_dept_name()

        try:
            with allure.step(f"修改部门: dept_id={dept_id}, 新名称={new_dept_name}"):
                resp_update = dept_api.update_dept(
                    dept_id=dept_id,
                    parent_id=ROOT_DEPT_ID,
                    dept_name=new_dept_name,
                    order_num=888,
                    status="0",
                )

            with allure.step("附加修改响应"):
                allure.attach(
                    body=str(resp_update),
                    name="UpdateDept Response",
                    attachment_type=allure.attachment_type.TEXT,
                )

            with allure.step("断言修改 code == 200"):
                assert resp_update.get("code") == 200, (
                    f"修改失败: code={resp_update.get('code')}, msg={resp_update.get('msg')}"
                )

            with allure.step(f"再次查详情验证修改: GET /system/dept/{dept_id}"):
                resp_get = dept_api.get_dept(dept_id)

            with allure.step("断言详情中 deptName 已更新"):
                data = resp_get.get("data", {})
                assert data.get("deptName") == new_dept_name, (
                    f"deptName 未更新: 期望 {new_dept_name!r}，实际 {data.get('deptName')!r}"
                )
                assert data.get("orderNum") == 888, (
                    f"orderNum 未更新: 期望 888，实际 {data.get('orderNum')}"
                )
        finally:
            with allure.step("清理：删除测试部门"):
                dept_api.delete_dept(dept_id)

    # ==================================================================
    # TC-SYS-DPT-016：新增后删除
    # ==================================================================

    @allure.story("删除部门")
    @allure.title("TC-SYS-DPT-016：新增部门后删除，断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_dept(self) -> None:
        """
        完整正向链路：新增部门 → DB 回查 dept_id → 删除，断言:
        - 删除响应 code == 200
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        dept_name, dept_id = _create_test_dept(dept_api)

        if dept_id is None:
            pytest.skip(f"DB 中未找到 deptName={dept_name}，跳过删除测试")

        allure.attach(
            body=f"dept_id={dept_id}\ndept_name={dept_name}",
            name="待删除部门信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用删除接口: DELETE /system/dept/{dept_id}"):
            resp = dept_api.delete_dept(dept_id)

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(resp),
                name="DeleteDept Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"删除失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

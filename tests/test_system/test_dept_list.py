"""
系统部门列表测试用例。

真实接口:
    GET http://192.168.0.107/dev-api/system/dept/list
        请求头: Authorization: Bearer <access_token>
        请求参数: deptName(模糊), status
        响应体: {"code": 200, "msg": "查询成功", "data": [...]}

    注意: 部门列表接口返回树形结构，顶层字段为 "data"（非分页的 rows/total）。

用例清单:
    TC-SYS-DPT-001  不带任何参数获取部门列表，断言 code==200 且 data 非空
    TC-SYS-DPT-002  按 deptName 模糊查询，断言 code==200
    TC-SYS-DPT-003  按 status="0" 筛选正常部门，断言 code==200
    TC-SYS-DPT-004  未携带 Token 获取列表，断言被鉴权拦截
"""
from __future__ import annotations

import allure
import pytest

from api.system.dept_api import SystemDeptAPI
from api.system.login_api import SystemLoginAPI


# ==============================================================================
# 辅助函数
# ==============================================================================

def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("部门管理")
class TestDeptList:
    """部门列表接口 GET /system/dept/list 测试集合。"""

    # ==================================================================
    # TC-SYS-DPT-001：默认参数获取部门列表
    # ==================================================================

    @allure.story("获取部门列表")
    @allure.title("TC-SYS-DPT-001：不带参数获取部门列表，断言 code==200 且 data 非空")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_list_depts_default(self) -> None:
        """
        不带任何过滤参数，断言:
        - 响应 code == 200
        - data 列表非空（系统初始化至少包含若干部门）
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        with allure.step("调用部门列表接口（默认参数）: GET /system/dept/list"):
            resp = dept_api.list_depts()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="DeptList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 data 非空"):
            data = resp.get("data", [])
            assert isinstance(data, list) and len(data) > 0, (
                f"data 应为非空列表，实际: {data!r}"
            )

    # ==================================================================
    # TC-SYS-DPT-002：按 deptName 模糊查询
    # ==================================================================

    @allure.story("获取部门列表")
    @allure.title("TC-SYS-DPT-002：按 deptName 模糊查询，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_depts_by_name(self) -> None:
        """
        传入 deptName 关键字模糊查询，断言:
        - 响应 code == 200
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        with allure.step("按 deptName='若依' 模糊查询: GET /system/dept/list"):
            resp = dept_api.list_depts(dept_name="若依")

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="DeptList ByName Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-DPT-003：按 status 筛选
    # ==================================================================

    @allure.story("获取部门列表")
    @allure.title("TC-SYS-DPT-003：按 status='0' 筛选正常部门，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_list_depts_by_status(self) -> None:
        """
        按 status="0" 筛选正常状态部门，断言:
        - 响应 code == 200
        """
        token = _login_and_get_token()
        dept_api = SystemDeptAPI()
        dept_api.set_token(token)

        with allure.step("按 status='0' 查询正常部门: GET /system/dept/list"):
            resp = dept_api.list_depts(status="0")

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="DeptList ByStatus Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"查询失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-DPT-004：未携带 Token 获取部门列表
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-DPT-004：未携带 Token 获取部门列表，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_list_depts_without_token(self) -> None:
        """
        不注入 Token 直接调用列表接口，断言:
        - 响应 code != 200（通常为 401）
        """
        dept_api = SystemDeptAPI()

        with allure.step("不注入 Token，调用部门列表接口"):
            resp = dept_api.list_depts()

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token DeptList Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

"""
系统用户新增 测试用例。

真实接口:
    POST  http://localhost:1024/dev-api/system/user
          请求头: Authorization: Bearer <access_token>
          请求体: {"userName": "...", "nickName": "...", "password": "...", ...}
          响应体: {"code": 200, "msg": "操作成功"}

用例清单:
    TC-SYS-USR-001  仅必填字段（userName/nickName/password）新增用户，断言 code==200
    TC-SYS-USR-002  全字段新增用户，断言 code==200 & 响应结构合法
    TC-SYS-USR-003  重复用户名新增，断言 code==500 且 msg 含"登录账号已存在"
    TC-SYS-USR-004  重复手机号新增，断言 code==500 且 msg 含"手机号码已存在"
    TC-SYS-USR-005  重复邮箱新增，断言 code==500 且 msg 含"邮箱账号已存在"
    TC-SYS-USR-006  未携带 Token 新增用户，断言被鉴权拦截
    TC-SYS-USR-007  数据驱动：文档所有部门 deptId 均可新增成功
    TC-SYS-USR-008  数据驱动：sex 枚举 0/1/2 均可新增成功
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.user_api import SystemUserAPI
from core.validator import Validator
from utils.db_client import DBClient


# ==============================================================================
# 辅助函数
# ==============================================================================

def _gen_username() -> str:
    """生成唯一用户名（取 UUID 前 8 位），防止用例间重名冲突。"""
    return "test_" + uuid.uuid4().hex[:8]


def _gen_phone() -> str:
    """生成唯一 11 位手机号（138 + 8 位数字）。"""
    return f"138{uuid.uuid4().int % 100_000_000:08d}"


def _login_and_get_token() -> str:
    """用 admin 账号登录，返回 access_token。"""
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("用户管理")
class TestAddUser:
    """新增用户接口 POST /system/user 测试集合。"""

    # ==================================================================
    # TC-SYS-USR-001：仅必填字段新增
    # ==================================================================

    @allure.story("正常新增用户")
    @allure.title("TC-SYS-USR-001：仅传必填字段（userName/nickName/password）新增用户成功")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_add_user_required_fields_only(self) -> None:
        """
        只传三个必填字段，断言:
        - 响应 code == 200
        - 响应 msg == "操作成功"
        """
        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        username = _gen_username()

        with allure.step(f"调用新增接口（仅必填字段）: userName={username}"):
            resp = user_api.add_user(
                user_name=username,
                nick_name="必填测试",
                password="Test@123456",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddUser Response",
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

    # ==================================================================
    # TC-SYS-USR-002：全字段新增
    # ==================================================================

    @allure.story("正常新增用户")
    @allure.title("TC-SYS-USR-002：全字段新增用户，断言 code==200 & 响应结构合法")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_user_all_fields(self) -> None:
        """
        传入文档中所有字段，断言:
        - 响应 code == 200
        - 响应结构符合 JSON Schema 契约
        """
        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        username = _gen_username()
        phonenumber = _gen_phone()
        email = username + "@test.com"

        with allure.step(f"调用新增接口（全字段）: userName={username}"):
            resp = user_api.add_user(
                user_name=username,
                nick_name="全字段测试",
                password="Test@123456",
                phonenumber=phonenumber,
                email=email,
                sex="0",
                status="0",
                dept_id=105,
                role_ids=[2],
                post_ids=[4],
                remark="自动化全字段测试",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddUser Full Fields Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言响应结构符合 JSON Schema 契约"):
            Validator.assert_schema(resp, "system_add_user_response")

    # ==================================================================
    # TC-SYS-USR-003：重复用户名
    # ==================================================================

    @allure.story("业务互斥拦截")
    @allure.title("TC-SYS-USR-003：重复用户名新增，code==500 且提示登录账号已存在")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_user_duplicate_username(self) -> None:
        """
        从 sys_user 表查询已存在的 user_name，直接尝试新增同名用户，断言:
        - code == 500
        - msg 包含"登录账号已存在"
        """
        with allure.step("从 sys_user 表查询已存在的 user_name"):
            db = DBClient.instance("ry_cloud")
            row = db.fetch_one(
                "SELECT user_name FROM sys_user "
                "WHERE del_flag = '0' AND user_name != '' AND LENGTH(user_name) > 5 "
                "ORDER BY RAND() ASC LIMIT 1"
            )
            if row is None:
                pytest.skip("sys_user 表中无可用记录，跳过重复用户名测试")
            existing_username = row["user_name"]

        allure.attach(
            body=f"已存在的 user_name: {existing_username}",
            name="DB 查询结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"使用已存在的 userName={existing_username} 调用新增接口，预期 code==500"):
            resp = user_api.add_user(
                user_name=existing_username,
                nick_name="重复用户名测试",
                password="Test@123456",
            )

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Duplicate Username Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 500"):
            assert resp.get("code") == 500, (
                f"期望 500，实际 code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step('断言 msg 含"登录账号已存在"'):
            assert "登录账号已存在" in resp.get("msg", ""), (
                f"msg 不含预期提示，实际: {resp.get('msg')!r}"
            )

    # ==================================================================
    # TC-SYS-USR-004：重复手机号
    # ==================================================================

    @allure.story("业务互斥拦截")
    @allure.title("TC-SYS-USR-004：重复手机号新增，code==500 且提示手机号码已存在")
    @allure.severity(allure.severity_level.NORMAL)
    def test_add_user_duplicate_phonenumber(self) -> None:
        """
        从 sys_user 表查询已存在的 phonenumber，直接尝试新增同手机号用户，断言:
        - code == 500
        - msg 包含"手机号码已存在"
        """
        with allure.step("从 sys_user 表查询已存在的非空 phonenumber"):
            db = DBClient.instance("ry_cloud")
            row = db.fetch_one(
                "SELECT phonenumber FROM sys_user "
                "WHERE del_flag = '0' AND phonenumber != '' "
                "ORDER BY user_id ASC LIMIT 1"
            )
            if row is None:
                pytest.skip("sys_user 表中无含手机号的记录，跳过重复手机号测试")
            existing_phone = row["phonenumber"]

        allure.attach(
            body=f"已存在的 phonenumber: {existing_phone}",
            name="DB 查询结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"使用不同用户名、已存在的 phonenumber={existing_phone} 调用新增接口，预期 code==500"):
            resp = user_api.add_user(
                user_name=_gen_username(),
                nick_name="手机号重复测试",
                password="Test@123456",
                phonenumber=existing_phone,
            )

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Duplicate Phone Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 500"):
            assert resp.get("code") == 500, (
                f"期望 500，实际 code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step('断言 msg 含"手机号码已存在"'):
            assert "手机号码已存在" in resp.get("msg", ""), (
                f"msg 不含预期提示，实际: {resp.get('msg')!r}"
            )

    # ==================================================================
    # TC-SYS-USR-005：重复邮箱
    # ==================================================================

    @allure.story("业务互斥拦截")
    @allure.title("TC-SYS-USR-005：重复邮箱新增，code==500 且提示邮箱账号已存在")
    @allure.severity(allure.severity_level.NORMAL)
    def test_add_user_duplicate_email(self) -> None:
        """
        从 sys_user 表查询已存在的 email，直接尝试新增同邮箱用户，断言:
        - code == 500
        - msg 包含"邮箱账号已存在"
        """
        with allure.step("从 sys_user 表查询已存在的非空 email"):
            db = DBClient.instance("ry_cloud")
            row = db.fetch_one(
                "SELECT email FROM sys_user "
                "WHERE del_flag = '0' AND email != '' "
                "ORDER BY user_id ASC LIMIT 1"
            )
            if row is None:
                pytest.skip("sys_user 表中无含邮箱的记录，跳过重复邮箱测试")
            existing_email = row["email"]

        allure.attach(
            body=f"已存在的 email: {existing_email}",
            name="DB 查询结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"使用不同用户名、已存在的 email={existing_email} 调用新增接口，预期 code==500"):
            resp = user_api.add_user(
                user_name=_gen_username(),
                nick_name="邮箱重复测试",
                password="Test@123456",
                email=existing_email,
            )

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Duplicate Email Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 500"):
            assert resp.get("code") == 500, (
                f"期望 500，实际 code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step('断言 msg 含"邮箱账号已存在"'):
            assert "邮箱账号已存在" in resp.get("msg", ""), (
                f"msg 不含预期提示，实际: {resp.get('msg')!r}"
            )

    # ==================================================================
    # TC-SYS-USR-006：未携带 Token
    # ==================================================================

    @allure.story("鉴权异常拦截")
    @allure.title("TC-SYS-USR-006：未携带 Token 新增用户，应被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_user_without_token(self) -> None:
        """
        不调用登录、不注入 token，直接调用 add_user，断言:
        - 响应 code 不为 200
        - msg 包含鉴权相关关键词
        """
        user_api = SystemUserAPI()  # 故意不 set_token

        with allure.step("不携带 Token，直接调用 add_user"):
            resp = user_api.add_user(
                user_name=_gen_username(),
                nick_name="鉴权测试",
                password="Test@123456",
            )

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="No-Token AddUser Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code 不为 200（应被鉴权拦截）"):
            assert resp.get("code") != 200, (
                f"未带 token 竟返回 200！响应: {resp}"
            )

        with allure.step("断言 msg 包含鉴权相关关键词"):
            msg = str(resp.get("msg", ""))
            keywords = ["令牌", "token", "认证", "登录", "未授权", "过期", "expire"]
            matched = any(kw.lower() in msg.lower() for kw in keywords)
            allure.attach(
                f"实际 msg: {msg!r}\n期望包含任意一个关键词: {keywords}",
                name="msg 关键词断言详情",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert matched, (
                f"msg 未包含鉴权提示关键词，实际 msg: {msg!r}，期望之一: {keywords}"
            )

    # ==================================================================
    # TC-SYS-USR-007：数据驱动 —— 不同部门
    # ==================================================================

    @allure.story("正常新增用户")
    @allure.title("TC-SYS-USR-007：数据驱动 - 文档所有部门 deptId 均可新增用户成功")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("dept_id,dept_name", [
        (103, "研发部门"),
        (104, "市场部门"),
        (105, "测试部门"),
        (106, "财务部门"),
        (107, "运维部门"),
    ])
    def test_add_user_different_dept(self, dept_id: int, dept_name: str) -> None:
        """数据驱动：对接口文档中每个部门各新增一个用户，均断言 code==200。"""
        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        username = _gen_username()

        with allure.step(f"新增用户至 {dept_name}（deptId={dept_id}）"):
            resp = user_api.add_user(
                user_name=username,
                nick_name=f"{dept_name}测试",
                password="Test@123456",
                dept_id=dept_id,
            )

        allure.attach(
            body=(
                f"userName={username}\n"
                f"deptId={dept_id}  ({dept_name})\n"
                f"code={resp.get('code')}\n"
                f"msg={resp.get('msg')}"
            ),
            name=f"部门 [{dept_name}] 新增结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"断言 code == 200（部门: {dept_name}）"):
            assert resp.get("code") == 200, (
                f"部门 {dept_name}（deptId={dept_id}）新增失败: {resp}"
            )

    # ==================================================================
    # TC-SYS-USR-008：数据驱动 —— 不同性别
    # ==================================================================

    @allure.story("正常新增用户")
    @allure.title("TC-SYS-USR-008：数据驱动 - sex 枚举 0/1/2 均可新增用户成功")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("sex,sex_label", [
        ("0", "男"),
        ("1", "女"),
        ("2", "未知"),
    ])
    def test_add_user_different_sex(self, sex: str, sex_label: str) -> None:
        """数据驱动：对 sex 枚举每个值各新增一个用户，均断言 code==200。"""
        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        username = _gen_username()

        with allure.step(f"新增用户，性别={sex_label}（sex={sex}）"):
            resp = user_api.add_user(
                user_name=username,
                nick_name=f"性别{sex_label}测试",
                password="Test@123456",
                sex=sex,
            )

        allure.attach(
            body=(
                f"userName={username}\n"
                f"sex={sex}  ({sex_label})\n"
                f"code={resp.get('code')}\n"
                f"msg={resp.get('msg')}"
            ),
            name=f"性别 [{sex_label}] 新增结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"断言 code == 200（性别: {sex_label}）"):
            assert resp.get("code") == 200, (
                f"sex={sex}（{sex_label}）新增失败: {resp}"
            )

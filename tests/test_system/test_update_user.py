"""
系统用户修改 测试用例。

真实接口:
    PUT  http://localhost:1024/dev-api/system/user
         请求头: Authorization: Bearer <access_token>
         请求体: {"userId": ..., "deptId": ..., ...可选字段...}
         响应体: {"code": 200, "msg": "操作成功"}

修改前置说明:
    userId / deptId 必须先从 sys_user 表查出后再传入接口，不可凭空构造。
    查询语句参考: SELECT user_id, dept_id, ... FROM sys_user WHERE user_id = %s

用例清单:
    TC-SYS-UPD-001  先新增用户，再修改昵称，断言 code==200 并回查 DB 验证
    TC-SYS-UPD-002  从 DB 取已有用户，同时修改多个字段，断言 code==200 并回查 DB 验证
    TC-SYS-UPD-003  修改邮箱为已存在的邮箱，断言 code==500 且 msg 含"邮箱账号已存在"
    TC-SYS-UPD-004  修改手机号为已存在的手机号，断言 code==500 且 msg 含"手机号码已存在"
    TC-SYS-UPD-005  未携带 Token 修改用户，断言被鉴权拦截
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.user_api import SystemUserAPI
from utils.db_client import DBClient
from utils.logger import logger


# ==============================================================================
# 辅助函数
# ==============================================================================

def _gen_username() -> str:
    return "test_" + uuid.uuid4().hex[:8]


def _gen_phone() -> str:
    return f"138{uuid.uuid4().int % 100_000_000:08d}"


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


def _query_user_by_id(user_id: int) -> dict | None:
    """从 sys_user 查询指定用户的完整信息（含 dept_id）。"""
    db = DBClient.instance("ry_cloud")
    return db.fetch_one(
        "SELECT user_id, user_name, nick_name, email, phonenumber, "
        "sex, status, dept_id, del_flag, remark "
        "FROM sys_user WHERE user_id = %s AND del_flag = '0' LIMIT 1",
        (user_id,),
    )


def _query_user_id_by_name(username: str) -> int | None:
    db = DBClient.instance("ry_cloud")
    row = db.fetch_one(
        "SELECT user_id FROM sys_user WHERE user_name = %s AND del_flag = '0' LIMIT 1",
        (username,),
    )
    return int(row["user_id"]) if row else None


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("用户管理")
class TestUpdateUser:
    """修改用户接口 PUT /system/user 测试集合。"""

    # ==================================================================
    # TC-SYS-UPD-001：先新增再修改（完整正向链路，单字段修改）
    # ==================================================================

    @allure.story("正常修改用户")
    @allure.title("TC-SYS-UPD-001：先新增用户，再修改昵称，断言 code==200 并回查 DB 验证")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_update_nick_name_after_add(self) -> None:
        """
        完整正向链路：
        1. 新增测试用户；
        2. 从 DB 查出 user_id 与 dept_id；
        3. 修改昵称；
        4. 断言 code==200；
        5. 回查 DB 验证昵称已更新。
        """
        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        username = _gen_username()
        new_nick = "自动化修改昵称"

        with allure.step(f"前置：新增测试用户 userName={username}"):
            logger.info("[UPD-001] 前置步骤：新增测试用户 userName={}", username)
            add_resp = user_api.add_user(
                user_name=username,
                nick_name="原始昵称",
                password="Test@123456",
                dept_id=105,
            )
            logger.debug("[UPD-001] 新增响应: {}", add_resp)
            assert add_resp.get("code") == 200, f"前置新增失败: {add_resp}"
            logger.info("[UPD-001] 用户新增成功 userName={}", username)

        with allure.step("从 DB 查询新增用户的 user_id 与 dept_id"):
            user_id = _query_user_id_by_name(username)
            if user_id is None:
                pytest.fail(f"DB 中未找到用户 {username}，无法继续修改测试")
            user_row = _query_user_by_id(user_id)
            dept_id = int(user_row["dept_id"])
            logger.info("[UPD-001] DB 查询到 user_id={} dept_id={}", user_id, dept_id)

        allure.attach(
            body=f"userName={username}\nuser_id={user_id}\ndept_id={dept_id}\n原昵称={user_row['nick_name']}",
            name="修改前用户信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用修改接口，将昵称改为 '{new_nick}'"):
            logger.info(
                "[UPD-001] 修改用户昵称 | user_id={} | 原昵称={} | 新昵称={}",
                user_id, user_row["nick_name"], new_nick,
            )
            resp = user_api.update_user(
                user_id=user_id,
                dept_id=dept_id,
                user_name=username,
                nick_name=new_nick,
            )
            logger.debug("[UPD-001] 修改响应: {}", resp)

        with allure.step("附加修改响应"):
            allure.attach(
                body=str(resp),
                name="UpdateUser Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"修改失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 msg == '操作成功'"):
            assert resp.get("msg") == "操作成功", f"msg 异常: {resp.get('msg')!r}"

        with allure.step("回查 DB 验证 nick_name 已更新"):
            logger.debug("[UPD-001] 回查 DB 验证修改结果")
            after_row = _query_user_by_id(user_id)
            actual_nick = after_row["nick_name"] if after_row else None
            allure.attach(
                body=(
                    f"user_id={user_id}\n"
                    f"期望 nick_name={new_nick!r}\n"
                    f"实际 nick_name={actual_nick!r}"
                ),
                name="DB 回查结果",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert actual_nick == new_nick, (
                f"DB 中 nick_name 未更新，期望={new_nick!r}，实际={actual_nick!r}"
            )
            logger.info(
                "[UPD-001] DB 验证通过 | user_id={} | nick_name={}",
                user_id, actual_nick,
            )

    # ==================================================================
    # TC-SYS-UPD-002：从 DB 取已有用户，同时修改多个字段
    # ==================================================================

    @allure.story("正常修改用户")
    @allure.title("TC-SYS-UPD-002：从 DB 取已有用户，同时修改多个字段，断言 code==200 并回查 DB 验证")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_multiple_fields(self) -> None:
        """
        从 DB 取 user_id >= 3 的普通用户，同时修改昵称、性别、备注，断言:
        - code == 200
        - DB 中三个字段均已更新
        """
        with allure.step("从 DB 查询 user_id >= 3 的普通用户"):
            logger.debug("[UPD-002] 查询 sys_user 获取候选用户")
            db = DBClient.instance("ry_cloud")
            row = db.fetch_one(
                "SELECT user_id, user_name, dept_id, nick_name, sex, remark "
                "FROM sys_user "
                "WHERE del_flag = '0' AND user_id >= 3 "
                "ORDER BY user_id DESC LIMIT 1"
            )
            if row is None:
                logger.warning("[UPD-002] sys_user 中无 user_id >= 3 的记录，跳过")
                pytest.skip("sys_user 中无 user_id >= 3 的可用记录，跳过测试")
            target_id = int(row["user_id"])
            target_dept = int(row["dept_id"])
            logger.info(
                "[UPD-002] 候选用户 | user_id={} | user_name={} | dept_id={}",
                target_id, row["user_name"], target_dept,
            )

        new_nick = "批量修改昵称"
        new_sex = "1"
        new_remark = "自动化多字段修改备注"

        allure.attach(
            body=(
                f"user_id={target_id}\nuser_name={row['user_name']}\n"
                f"dept_id={target_dept}\n"
                f"原 nick_name={row['nick_name']}\n"
                f"原 sex={row['sex']}\n"
                f"原 remark={row['remark']}"
            ),
            name="修改前用户信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"调用修改接口，修改 nick_name / sex / remark"):
            logger.info(
                "[UPD-002] 修改多字段 | user_id={} | nick_name={} | sex={} | remark={}",
                target_id, new_nick, new_sex, new_remark,
            )
            resp = user_api.update_user(
                user_id=target_id,
                dept_id=target_dept,
                user_name=row["user_name"],
                nick_name=new_nick,
                sex=new_sex,
                remark=new_remark,
            )
            logger.debug("[UPD-002] 修改响应: {}", resp)

        with allure.step("附加修改响应"):
            allure.attach(
                body=str(resp),
                name="UpdateUser Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"修改失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 msg == '操作成功'"):
            assert resp.get("msg") == "操作成功", f"msg 异常: {resp.get('msg')!r}"

        with allure.step("回查 DB 验证三个字段均已更新"):
            logger.debug("[UPD-002] 回查 DB 验证修改结果")
            after = _query_user_by_id(target_id)
            allure.attach(
                body=(
                    f"user_id={target_id}\n"
                    f"nick_name: 期望={new_nick!r}，实际={after['nick_name']!r}\n"
                    f"sex: 期望={new_sex!r}，实际={after['sex']!r}\n"
                    f"remark: 期望={new_remark!r}，实际={after['remark']!r}"
                ),
                name="DB 回查结果",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert after["nick_name"] == new_nick, (
                f"nick_name 未更新，期望={new_nick!r}，实际={after['nick_name']!r}"
            )
            assert after["sex"] == new_sex, (
                f"sex 未更新，期望={new_sex!r}，实际={after['sex']!r}"
            )
            assert after["remark"] == new_remark, (
                f"remark 未更新，期望={new_remark!r}，实际={after['remark']!r}"
            )
            logger.info(
                "[UPD-002] DB 验证通过 | user_id={} | nick_name={} | sex={} | remark={}",
                target_id, after["nick_name"], after["sex"], after["remark"],
            )

    # ==================================================================
    # TC-SYS-UPD-003：修改邮箱为已存在邮箱
    # ==================================================================

    @allure.story("业务互斥拦截")
    @allure.title("TC-SYS-UPD-003：修改邮箱为已存在的邮箱，code==500 且提示邮箱账号已存在")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_duplicate_email(self) -> None:
        """
        从 DB 取两条不同用户：
        - 目标用户（将被修改）；
        - 已有邮箱（从另一用户获取）；
        断言修改时 code==500 且 msg 含"邮箱账号已存在"。
        """
        db = DBClient.instance("ry_cloud")

        with allure.step("从 DB 查询一个已有非空邮箱的用户（邮箱来源）"):
            logger.debug("[UPD-003] 查询已有邮箱用户")
            email_row = db.fetch_one(
                "SELECT user_id, email FROM sys_user "
                "WHERE del_flag = '0' AND email != '' AND email IS NOT NULL "
                "ORDER BY user_id ASC LIMIT 1"
            )
            if email_row is None:
                pytest.skip("sys_user 中无含邮箱的记录，跳过重复邮箱修改测试")
            existing_email = email_row["email"]
            existing_email_uid = int(email_row["user_id"])
            logger.info("[UPD-003] 已有邮箱 email={} 来自 user_id={}", existing_email, existing_email_uid)

        with allure.step("从 DB 查询另一个不同用户作为修改目标"):
            logger.debug("[UPD-003] 查询修改目标用户（user_id >= 3，排除邮箱来源用户）")
            target_row = db.fetch_one(
                "SELECT user_id, user_name, dept_id FROM sys_user "
                "WHERE del_flag = '0' AND user_id >= 3 AND user_id != %s "
                "ORDER BY user_id DESC LIMIT 1",
                (existing_email_uid,),
            )
            if target_row is None:
                pytest.skip("找不到可作为修改目标的用户，跳过测试")
            target_id = int(target_row["user_id"])
            target_dept = int(target_row["dept_id"])
            logger.info(
                "[UPD-003] 修改目标 user_id={} user_name={}",
                target_id, target_row["user_name"],
            )

        allure.attach(
            body=(
                f"修改目标 user_id={target_id}\n"
                f"试图写入的重复 email={existing_email}\n"
                f"该邮箱已属于 user_id={existing_email_uid}"
            ),
            name="测试数据",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"将 user_id={target_id} 的邮箱修改为已存在的 {existing_email}"):
            logger.info(
                "[UPD-003] 尝试写入重复邮箱 | user_id={} | email={}",
                target_id, existing_email,
            )
            resp = user_api.update_user(
                user_id=target_id,
                dept_id=target_dept,
                user_name=target_row["user_name"],
                email=existing_email,
            )
            logger.debug("[UPD-003] 响应: {}", resp)

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Duplicate Email Update Response",
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
            logger.info(
                "[UPD-003] 按预期被拦截 | code={} | msg={}",
                resp.get("code"), resp.get("msg"),
            )

    # ==================================================================
    # TC-SYS-UPD-004：修改手机号为已存在手机号
    # ==================================================================

    @allure.story("业务互斥拦截")
    @allure.title("TC-SYS-UPD-004：修改手机号为已存在的手机号，code==500 且提示手机号码已存在")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_duplicate_phonenumber(self) -> None:
        """
        从 DB 取两条不同用户：
        - 目标用户（将被修改）；
        - 已有手机号（从另一用户获取）；
        断言修改时 code==500 且 msg 含"手机号码已存在"。
        """
        db = DBClient.instance("ry_cloud")

        with allure.step("从 DB 查询一个已有非空手机号的用户（手机号来源）"):
            logger.debug("[UPD-004] 查询已有手机号用户")
            phone_row = db.fetch_one(
                "SELECT user_id, phonenumber FROM sys_user "
                "WHERE del_flag = '0' AND phonenumber != '' AND phonenumber IS NOT NULL "
                "ORDER BY user_id ASC LIMIT 1"
            )
            if phone_row is None:
                pytest.skip("sys_user 中无含手机号的记录，跳过重复手机号修改测试")
            existing_phone = phone_row["phonenumber"]
            existing_phone_uid = int(phone_row["user_id"])
            logger.info(
                "[UPD-004] 已有手机号 phonenumber={} 来自 user_id={}",
                existing_phone, existing_phone_uid,
            )

        with allure.step("从 DB 查询另一个不同用户作为修改目标"):
            logger.debug("[UPD-004] 查询修改目标用户（排除手机号来源用户）")
            target_row = db.fetch_one(
                "SELECT user_id, user_name, dept_id FROM sys_user "
                "WHERE del_flag = '0' AND user_id >= 3 AND user_id != %s "
                "ORDER BY user_id DESC LIMIT 1",
                (existing_phone_uid,),
            )
            if target_row is None:
                pytest.skip("找不到可作为修改目标的用户，跳过测试")
            target_id = int(target_row["user_id"])
            target_dept = int(target_row["dept_id"])
            logger.info(
                "[UPD-004] 修改目标 user_id={} user_name={}",
                target_id, target_row["user_name"],
            )

        allure.attach(
            body=(
                f"修改目标 user_id={target_id}\n"
                f"试图写入的重复 phonenumber={existing_phone}\n"
                f"该手机号已属于 user_id={existing_phone_uid}"
            ),
            name="测试数据",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"将 user_id={target_id} 的手机号修改为已存在的 {existing_phone}"):
            logger.info(
                "[UPD-004] 尝试写入重复手机号 | user_id={} | phonenumber={}",
                target_id, existing_phone,
            )
            resp = user_api.update_user(
                user_id=target_id,
                dept_id=target_dept,
                user_name=target_row["user_name"],
                phonenumber=existing_phone,
            )
            logger.debug("[UPD-004] 响应: {}", resp)

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Duplicate Phone Update Response",
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
            logger.info(
                "[UPD-004] 按预期被拦截 | code={} | msg={}",
                resp.get("code"), resp.get("msg"),
            )

    # ==================================================================
    # TC-SYS-UPD-005：未携带 Token
    # ==================================================================

    @allure.story("鉴权异常拦截")
    @allure.title("TC-SYS-UPD-005：未携带 Token 修改用户，应被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_user_without_token(self) -> None:
        """
        不注入 Token，直接调用 update_user，断言:
        - code 不为 200
        - msg 包含鉴权相关关键词
        """
        user_api = SystemUserAPI()  # 故意不 set_token

        with allure.step("不携带 Token，调用 PUT /system/user"):
            logger.info("[UPD-005] 未注入 Token，发起修改请求，预期被鉴权拦截")
            resp = user_api.update_user(user_id=1, dept_id=103, user_name="admin", nick_name="鉴权测试")
            logger.debug("[UPD-005] 响应: {}", resp)

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="No-Token UpdateUser Response",
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
            logger.info(
                "[UPD-005] 鉴权拦截验证通过 | code={} | msg={}",
                resp.get("code"), msg,
            )

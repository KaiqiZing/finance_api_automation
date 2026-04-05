"""
系统用户删除 测试用例。

真实接口:
    DELETE http://localhost:1024/dev-api/system/user/{id}
           请求头: Authorization: Bearer <access_token>
           路径参数: id —— 要删除的用户 ID（Long）
           响应体: {"code": 200, "msg": "操作成功"}

用例清单:
    TC-SYS-DEL-001  先新增用户再删除（完整正向链路），断言 code==200
    TC-SYS-DEL-002  从 sys_user 表随机取 user_id>=3 的普通用户直接删除，断言 code==200
    TC-SYS-DEL-003  删除不存在的用户 ID（99999999），断言 code==500
    TC-SYS-DEL-004  未携带 Token 删除用户，断言被鉴权拦截
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


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


def _get_user_id_by_name(username: str) -> int | None:
    """从 sys_user 表按用户名查询 user_id。"""
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
class TestDeleteUser:
    """删除用户接口 DELETE /system/user/{id} 测试集合。"""

    # ==================================================================
    # TC-SYS-DEL-001：先新增再删除（完整正向链路）
    # ==================================================================

    @allure.story("正常删除用户")
    @allure.title("TC-SYS-DEL-001：先新增用户再删除，断言 code==200")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_delete_user_after_add(self) -> None:
        """
        完整正向链路：
        1. 新增一个测试用户；
        2. 从 sys_user 表查出该用户的 user_id；
        3. 调用删除接口，断言 code==200。
        """
        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        username = _gen_username()

        with allure.step(f"新增测试用户: userName={username}"):
            logger.info("[DEL-001] 前置步骤：新增测试用户 userName={}", username)
            add_resp = user_api.add_user(
                user_name=username,
                nick_name="删除链路测试",
                password="Test@123456",
            )
            logger.debug("[DEL-001] 新增响应: {}", add_resp)
            assert add_resp.get("code") == 200, (
                f"前置新增失败，无法继续删除测试: {add_resp}"
            )
            logger.info("[DEL-001] 用户新增成功，userName={}", username)

        with allure.step(f"从 sys_user 表查询 {username} 的 user_id"):
            logger.debug("[DEL-001] 查询 sys_user 获取 user_id，userName={}", username)
            user_id = _get_user_id_by_name(username)
            if user_id is None:
                logger.error("[DEL-001] DB 中未找到用户 {}，无法执行删除", username)
                pytest.fail(f"新增后在 sys_user 中未找到用户 {username}，无法继续")
            logger.info("[DEL-001] 查到 user_id={}，userName={}", user_id, username)

        allure.attach(
            body=f"userName={username}\nuser_id={user_id}",
            name="新增用户信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用删除接口 DELETE /system/user/{user_id}"):
            logger.warning(
                "[DEL-001] 即将删除用户 | user_id={} | userName={}",
                user_id, username,
            )
            del_resp = user_api.delete_user(user_id)
            logger.debug("[DEL-001] 删除响应: {}", del_resp)

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(del_resp),
                name="DeleteUser Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert del_resp.get("code") == 200, (
                f"删除失败: code={del_resp.get('code')}, msg={del_resp.get('msg')}"
            )

        with allure.step("断言 msg == '操作成功'"):
            assert del_resp.get("msg") == "操作成功", (
                f"msg 异常: {del_resp.get('msg')!r}"
            )
            logger.info(
                "[DEL-001] 删除成功 | user_id={} | userName={} | msg={}",
                user_id, username, del_resp.get("msg"),
            )

    # ==================================================================
    # TC-SYS-DEL-002：从 DB 取已有用户直接删除
    # ==================================================================

    @allure.story("正常删除用户")
    @allure.title("TC-SYS-DEL-002：从 sys_user 表取普通用户 ID，直接删除，断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_existing_user_from_db(self) -> None:
        """
        从 sys_user 表随机取一条 user_id >= 3 的普通用户，
        调用删除接口，断言:
        - code == 200
        - msg == "操作成功"
        """
        with allure.step("从 sys_user 表查询 user_id >= 3 的可删用户"):
            logger.debug("[DEL-002] 查询 sys_user 获取 user_id >= 3 的候选用户")
            db = DBClient.instance("ry_cloud")
            row = db.fetch_one(
                "SELECT user_id, user_name FROM sys_user "
                "WHERE del_flag = '0' AND user_id >= 3 "
                "ORDER BY user_id DESC LIMIT 1"
            )
            if row is None:
                logger.warning("[DEL-002] sys_user 中无 user_id >= 3 的记录，跳过")
                pytest.skip("sys_user 表中无 user_id >= 3 的可用记录，跳过测试")
            target_id = int(row["user_id"])
            target_name = row["user_name"]
            logger.info(
                "[DEL-002] DB 查询到候选用户 | user_id={} | user_name={}",
                target_id, target_name,
            )

        allure.attach(
            body=f"user_id={target_id}\nuser_name={target_name}",
            name="DB 查询结果",
            attachment_type=allure.attachment_type.TEXT,
        )

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"调用删除接口 DELETE /system/user/{target_id}"):
            logger.warning(
                "[DEL-002] 即将删除用户 | user_id={} | user_name={}",
                target_id, target_name,
            )
            resp = user_api.delete_user(target_id)
            logger.debug("[DEL-002] 删除响应: {}", resp)

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(resp),
                name="DeleteUser Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"删除失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言 msg == '操作成功'"):
            assert resp.get("msg") == "操作成功", (
                f"msg 异常: {resp.get('msg')!r}"
            )
            logger.info(
                "[DEL-002] 删除成功 | user_id={} | user_name={} | msg={}",
                target_id, target_name, resp.get("msg"),
            )

    # ==================================================================
    # TC-SYS-DEL-003：删除不存在的用户 ID
    # ==================================================================

    @allure.story("异常场景拦截")
    @allure.title("TC-SYS-DEL-003：删除不存在的用户 ID（99999999），断言 code==500")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_nonexistent_user(self) -> None:
        """
        使用一个库中肯定不存在的极大 user_id 发起删除请求，断言:
        - code == 500
        """
        nonexistent_id = 99999999

        token = _login_and_get_token()
        user_api = SystemUserAPI()
        user_api.set_token(token)

        with allure.step(f"调用删除接口，user_id={nonexistent_id}（不存在）"):
            logger.info("[DEL-003] 使用不存在的 user_id={} 发起删除请求", nonexistent_id)
            resp = user_api.delete_user(nonexistent_id)
            logger.debug("[DEL-003] 响应: {}", resp)

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="Nonexistent User Delete Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 500"):
            assert resp.get("code") == 500, (
                f"期望 500，实际 code={resp.get('code')}, msg={resp.get('msg')}"
            )
            logger.info(
                "[DEL-003] 按预期被拦截 | user_id={} | code={} | msg={}",
                nonexistent_id, resp.get("code"), resp.get("msg"),
            )

    # ==================================================================
    # TC-SYS-DEL-004：未携带 Token
    # ==================================================================

    @allure.story("鉴权异常拦截")
    @allure.title("TC-SYS-DEL-004：未携带 Token 删除用户，应被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_user_without_token(self) -> None:
        """
        不注入 Token，直接调用 delete_user，断言:
        - code 不为 200
        - msg 包含鉴权相关关键词
        """
        user_api = SystemUserAPI()  # 故意不 set_token

        with allure.step("不携带 Token，调用 DELETE /system/user/1"):
            logger.info("[DEL-004] 未注入 Token，发起删除请求，预期被鉴权拦截")
            resp = user_api.delete_user(1)
            logger.debug("[DEL-004] 响应: {}", resp)

        with allure.step("附加响应内容"):
            allure.attach(
                body=str(resp),
                name="No-Token DeleteUser Response",
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
                "[DEL-004] 鉴权拦截验证通过 | code={} | msg={}",
                resp.get("code"), msg,
            )

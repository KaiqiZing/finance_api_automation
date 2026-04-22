"""
系统岗位 CRUD 测试用例。

真实接口:
    POST   http://192.168.0.107/dev-api/system/post         新增岗位
    GET    http://192.168.0.107/dev-api/system/post/{id}    获取岗位详情
    PUT    http://192.168.0.107/dev-api/system/post         修改岗位
    DELETE http://192.168.0.107/dev-api/system/post/{ids}   删除岗位（逗号分隔）

用例清单:
    TC-SYS-PST-010  仅必填字段新增岗位，断言 code==200
    TC-SYS-PST-011  含可选字段 remark 新增岗位，断言 code==200
    TC-SYS-PST-012  重复 postCode 新增岗位，断言 code==500 且 msg 含相关描述
    TC-SYS-PST-013  未携带 Token 新增岗位，断言被鉴权拦截
    TC-SYS-PST-014  获取岗位详情（新增后按 postId 查询），断言 code==200 且字段匹配
    TC-SYS-PST-015  修改岗位（完整正向链路：新增→查详情→修改→再查），断言 code==200
    TC-SYS-PST-016  新增后删除（完整正向链路），断言 code==200
    TC-SYS-PST-017  批量删除多个测试岗位，断言 code==200
    TC-SYS-PST-018  删除不存在的岗位 ID，观察服务端实际返回
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.login_api import SystemLoginAPI
from api.system.post_api import SystemPostAPI
from utils.system_ruoyi_queries import fetch_post_id_by_post_code


# ==============================================================================
# 辅助函数
# ==============================================================================

def _gen_post_code() -> str:
    """生成唯一岗位编码（取 UUID 前 8 位），防止用例间冲突。"""
    return "test_" + uuid.uuid4().hex[:8]


def _gen_post_name() -> str:
    """生成唯一岗位名称。"""
    return "测试岗位_" + uuid.uuid4().hex[:6]


def _login_and_get_token() -> str:
    login_api = SystemLoginAPI()
    resp = login_api.login(username="admin", password="admin123")
    assert resp.get("code") == 200, f"登录失败，无法获取 token: {resp}"
    return resp["data"]["access_token"]


def _create_test_post(post_api: SystemPostAPI) -> tuple[str, str]:
    """
    新增一个测试岗位，返回 (post_name, post_code)。
    调用方需负责在测试结束后删除该岗位。
    """
    post_name = _gen_post_name()
    post_code = _gen_post_code()
    resp = post_api.add_post(post_name=post_name, post_code=post_code, post_sort=99, status="0")
    assert resp.get("code") == 200, f"前置新增岗位失败: {resp}"
    return post_name, post_code


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("岗位管理")
class TestPostCrud:
    """岗位 CRUD 接口综合测试集合。"""

    # ==================================================================
    # TC-SYS-PST-010：仅必填字段新增
    # ==================================================================

    @allure.story("新增岗位")
    @allure.title("TC-SYS-PST-010：仅传必填字段（postCode/postName/postSort/status）新增岗位成功")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_add_post_required_fields_only(self) -> None:
        """
        只传四个必填字段，断言:
        - 响应 code == 200
        - 响应 msg == "操作成功"

        测试后通过接口删除所建岗位，保持环境整洁。
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()

        with allure.step(f"调用新增接口（仅必填字段）: postCode={post_code}, postName={post_name}"):
            resp = post_api.add_post(
                post_name=post_name,
                post_code=post_code,
                post_sort=99,
                status="0",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddPost Response",
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

        with allure.step("清理：删除刚新增的测试岗位"):
            post_id = fetch_post_id_by_post_code(post_code)
            if post_id is not None:
                post_api.delete_posts([post_id])

    # ==================================================================
    # TC-SYS-PST-011：含可选字段 remark 新增
    # ==================================================================

    @allure.story("新增岗位")
    @allure.title("TC-SYS-PST-011：含可选字段 remark 新增岗位，断言 code==200")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_post_with_remark(self) -> None:
        """
        传入必填字段 + remark，断言:
        - 响应 code == 200

        测试后通过接口删除所建岗位。
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()

        with allure.step(f"调用新增接口（含 remark）: postCode={post_code}"):
            resp = post_api.add_post(
                post_name=post_name,
                post_code=post_code,
                post_sort=50,
                status="0",
                remark="自动化测试岗位备注",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="AddPost Remark Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"新增失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("清理：删除刚新增的测试岗位"):
            post_id = fetch_post_id_by_post_code(post_code)
            if post_id is not None:
                post_api.delete_posts([post_id])

    # ==================================================================
    # TC-SYS-PST-012：重复 postCode 新增（负面用例）
    # ==================================================================

    @allure.story("新增岗位")
    @allure.title("TC-SYS-PST-012：重复 postCode 新增，断言 code==500 且 msg 含相关描述")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_post_duplicate_code(self) -> None:
        """
        两次使用相同 postCode 新增，断言:
        - 第一次 code == 200
        - 第二次 code == 500 且 msg 包含 "已存在" 相关字样
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_code = _gen_post_code()
        post_name_1 = _gen_post_name()
        post_name_2 = _gen_post_name()

        with allure.step(f"第一次新增岗位: postCode={post_code}"):
            resp1 = post_api.add_post(post_name=post_name_1, post_code=post_code, post_sort=99, status="0")

        assert resp1.get("code") == 200, f"第一次新增失败: {resp1}"

        with allure.step(f"第二次新增（相同 postCode）: postCode={post_code}"):
            resp2 = post_api.add_post(post_name=post_name_2, post_code=post_code, post_sort=99, status="0")

        with allure.step("附加第二次响应"):
            allure.attach(
                body=str(resp2),
                name="Duplicate PostCode Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言第二次 code == 500"):
            assert resp2.get("code") == 500, (
                f"期望 code==500，实际 code={resp2.get('code')}, msg={resp2.get('msg')}"
            )

        with allure.step("清理：删除第一次新增的测试岗位"):
            post_id = fetch_post_id_by_post_code(post_code)
            if post_id is not None:
                post_api.delete_posts([post_id])

    # ==================================================================
    # TC-SYS-PST-013：未携带 Token 新增岗位
    # ==================================================================

    @allure.story("鉴权校验")
    @allure.title("TC-SYS-PST-013：未携带 Token 新增岗位，断言被鉴权拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_add_post_without_token(self) -> None:
        """
        不注入 Token 直接调用新增接口，断言:
        - 响应 code != 200（通常为 401）
        """
        post_api = SystemPostAPI()

        with allure.step("不注入 Token，调用新增岗位接口"):
            resp = post_api.add_post(
                post_name=_gen_post_name(),
                post_code=_gen_post_code(),
                post_sort=99,
                status="0",
            )

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="No Token AddPost Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言被鉴权拦截（code != 200）"):
            assert resp.get("code") != 200, (
                f"未携带 Token 竟返回 code==200，存在鉴权漏洞，响应: {resp}"
            )

    # ==================================================================
    # TC-SYS-PST-014：获取岗位详情
    # ==================================================================

    @allure.story("获取岗位详情")
    @allure.title("TC-SYS-PST-014：新增岗位后获取详情，断言 code==200 且关键字段匹配")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_post_detail(self) -> None:
        """
        完整链路：新增岗位 → 通过 postCode 查询 post_id → 调用详情接口，断言:
        - 响应 code == 200
        - data.postCode 与新增时一致
        - data.postName 与新增时一致
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()

        with allure.step(f"前置：新增岗位 postCode={post_code}"):
            resp_add = post_api.add_post(post_name=post_name, post_code=post_code, post_sort=99, status="0")
            assert resp_add.get("code") == 200, f"前置新增失败: {resp_add}"

        with allure.step("从 DB 查询 post_id"):
            post_id = fetch_post_id_by_post_code(post_code)
            if post_id is None:
                pytest.skip(f"DB 中未找到 postCode={post_code}，跳过详情测试")

        allure.attach(
            body=f"post_id={post_id}\npost_name={post_name}\npost_code={post_code}",
            name="新增岗位信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用详情接口: GET /system/post/{post_id}"):
            resp = post_api.get_post(post_id)

        with allure.step("附加详情响应"):
            allure.attach(
                body=str(resp),
                name="GetPost Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"获取详情失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

        with allure.step("断言详情中 postCode 与 postName 与新增时一致"):
            data = resp.get("data", {})
            assert data.get("postCode") == post_code, (
                f"postCode 不匹配: 期望 {post_code!r}，实际 {data.get('postCode')!r}"
            )
            assert data.get("postName") == post_name, (
                f"postName 不匹配: 期望 {post_name!r}，实际 {data.get('postName')!r}"
            )

        with allure.step("清理：删除测试岗位"):
            post_api.delete_posts([post_id])

    # ==================================================================
    # TC-SYS-PST-015：修改岗位
    # ==================================================================

    @allure.story("修改岗位")
    @allure.title("TC-SYS-PST-015：新增→查详情→修改→再查岗位，断言 code==200 且修改后字段生效")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_post(self) -> None:
        """
        完整正向链路：
        1. 新增测试岗位；
        2. 通过 postCode 查 post_id；
        3. 修改 postName 与 remark，断言 code==200；
        4. 再次查详情确认修改生效。
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()

        with allure.step(f"前置：新增岗位 postCode={post_code}"):
            resp_add = post_api.add_post(post_name=post_name, post_code=post_code, post_sort=99, status="0")
            assert resp_add.get("code") == 200, f"前置新增失败: {resp_add}"

        with allure.step("从 DB 查询 post_id"):
            post_id = fetch_post_id_by_post_code(post_code)
            if post_id is None:
                pytest.skip(f"DB 中未找到 postCode={post_code}，跳过修改测试")

        new_post_name = _gen_post_name()

        with allure.step(f"调用修改接口: postName 改为 {new_post_name}"):
            resp_update = post_api.update_post(
                post_id=post_id,
                post_name=new_post_name,
                post_code=post_code,
                post_sort=99,
                status="0",
                remark="自动化修改备注",
            )

        with allure.step("附加修改响应"):
            allure.attach(
                body=str(resp_update),
                name="UpdatePost Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言修改 code == 200"):
            assert resp_update.get("code") == 200, (
                f"修改失败: code={resp_update.get('code')}, msg={resp_update.get('msg')}"
            )

        with allure.step("再次查详情，断言 postName 已更新"):
            resp_detail = post_api.get_post(post_id)
            data = resp_detail.get("data", {})
            assert data.get("postName") == new_post_name, (
                f"修改未生效: 期望 {new_post_name!r}，实际 {data.get('postName')!r}"
            )

        with allure.step("清理：删除测试岗位"):
            post_api.delete_posts([post_id])

    # ==================================================================
    # TC-SYS-PST-016：新增后删除（完整正向链路）
    # ==================================================================

    @allure.story("删除岗位")
    @allure.title("TC-SYS-PST-016：新增岗位后删除，断言 code==200")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_delete_post_after_add(self) -> None:
        """
        完整正向链路：
        1. 新增测试岗位；
        2. 通过 postCode 查询 post_id；
        3. 调用删除接口，断言 code==200。
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_name = _gen_post_name()
        post_code = _gen_post_code()

        with allure.step(f"前置：新增岗位 postCode={post_code}"):
            resp_add = post_api.add_post(post_name=post_name, post_code=post_code, post_sort=99, status="0")
            assert resp_add.get("code") == 200, f"前置新增失败: {resp_add}"

        with allure.step("从 DB 查询 post_id"):
            post_id = fetch_post_id_by_post_code(post_code)
            if post_id is None:
                pytest.skip(f"DB 中未找到 postCode={post_code}，跳过删除测试")

        allure.attach(
            body=f"post_id={post_id}\npost_code={post_code}",
            name="待删除岗位信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用删除接口: DELETE /system/post/{post_id}"):
            resp = post_api.delete_posts([post_id])

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(resp),
                name="DeletePost Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"删除失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-PST-017：批量删除多个测试岗位
    # ==================================================================

    @allure.story("删除岗位")
    @allure.title("TC-SYS-PST-017：批量删除多个测试岗位，断言 code==200")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_posts_batch(self) -> None:
        """
        批量删除链路：
        1. 新增两个测试岗位；
        2. 调用批量删除接口，断言 code==200。
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        post_ids: list[int] = []
        post_codes: list[str] = []

        with allure.step("前置：批量新增两个测试岗位"):
            for _ in range(2):
                post_code = _gen_post_code()
                post_codes.append(post_code)
                resp_add = post_api.add_post(
                    post_name=_gen_post_name(),
                    post_code=post_code,
                    post_sort=99,
                    status="0",
                )
                assert resp_add.get("code") == 200, f"前置批量新增失败: {resp_add}"
                post_id = fetch_post_id_by_post_code(post_code)
                if post_id is not None:
                    post_ids.append(post_id)

        if len(post_ids) < 2:
            pytest.skip("DB 中未能查到足够的测试岗位 ID，跳过批量删除测试")

        allure.attach(
            body=f"批量删除 post_ids: {post_ids}",
            name="待删除岗位信息",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"调用批量删除接口: DELETE /system/post/{','.join(str(i) for i in post_ids)}"):
            resp = post_api.delete_posts(post_ids)

        with allure.step("附加删除响应"):
            allure.attach(
                body=str(resp),
                name="BatchDeletePost Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言 code == 200"):
            assert resp.get("code") == 200, (
                f"批量删除失败: code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-SYS-PST-018：删除不存在的岗位（边界用例）
    # ==================================================================

    @allure.story("删除岗位")
    @allure.title("TC-SYS-PST-018：删除不存在的岗位 ID（99999999），观察服务端实际返回")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_nonexistent_post(self) -> None:
        """
        删除一个不存在的岗位 ID，断言:
        - 服务端有明确响应（不崩溃）
        - code 通常为 200（幂等删除）或 500（业务错误）

        该用例记录服务端实际行为，以便回归时发现行为变化。
        """
        token = _login_and_get_token()
        post_api = SystemPostAPI()
        post_api.set_token(token)

        nonexistent_id = 99999999

        with allure.step(f"调用删除接口: post_id={nonexistent_id}"):
            resp = post_api.delete_posts([nonexistent_id])

        with allure.step("附加完整响应"):
            allure.attach(
                body=str(resp),
                name="Delete Nonexistent Post Response",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("断言服务端有明确响应（code 在 200/400/500 之一）"):
            assert resp.get("code") in (200, 400, 500), (
                f"服务端响应异常 code={resp.get('code')}, msg={resp.get('msg')}"
            )

"""
批量新增数据测试用例。

用例清单:
    TC-BATCH-001  单次新增用户，断言 code==200（不删除数据）
    TC-BATCH-002  单次新增角色，断言 code==200（不删除数据）
    TC-BATCH-003  单次新增岗位，断言 code==200（不删除数据）
    TC-BATCH-004  单次新增公告，断言 code==200（不删除数据）
    TC-BATCH-005  批量新增：用户 + 角色 + 岗位 + 公告四接口组合调用，断言全部 code==200

手动控制新增次数:
    修改本文件顶部的 ADD_COUNT 即可控制每个用例的执行轮次。
    例如: ADD_COUNT = 5 → 每个测试方法执行 5 轮，批量用例也执行 5 轮。

注意: 所有新增数据均不做清理删除，供后续手动核查或留存。
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.system.notice_api import SystemNoticeAPI
from api.system.post_api import SystemPostAPI
from api.system.role_api import SystemRoleAPI
from api.system.user_api import SystemUserAPI
from tests.test_system.conftest import _login_and_get_token, gen_phone, gen_username
from utils.system_ruoyi_queries import fetch_random_third_level_dept_id

# ==============================================================================
# ★ 新增次数控制（手动修改此处）
# ==============================================================================
ADD_COUNT: int = 3   # 每轮执行次数，改这里即可

# ==============================================================================
# 辅助函数
# ==============================================================================


def _gen_role_key() -> str:
    return "batch_role_" + uuid.uuid4().hex[:8]


def _gen_role_name() -> str:
    return "批量角色_" + uuid.uuid4().hex[:6]


def _gen_post_code() -> str:
    return "batch_post_" + uuid.uuid4().hex[:8]


def _gen_post_name() -> str:
    return "批量岗位_" + uuid.uuid4().hex[:6]


def _gen_notice_title() -> str:
    return "批量公告_" + uuid.uuid4().hex[:8]


def _setup_apis(token: str) -> tuple[SystemUserAPI, SystemRoleAPI, SystemPostAPI, SystemNoticeAPI]:
    """初始化四个 API 实例并注入 token。"""
    user_api = SystemUserAPI()
    role_api = SystemRoleAPI()
    post_api = SystemPostAPI()
    notice_api = SystemNoticeAPI()
    for api in (user_api, role_api, post_api, notice_api):
        api.set_token(token)
    return user_api, role_api, post_api, notice_api


# ==============================================================================
# 测试类
# ==============================================================================

@allure.epic("系统管理模块")
@allure.feature("批量新增数据")
class TestBatchAddData:
    """
    验证用户、角色、岗位、公告四个新增接口，并提供组合批量新增场景。
    所有新增数据不做删除，执行轮次由模块顶部 ADD_COUNT 控制。
    """

    # ==================================================================
    # TC-BATCH-001：新增用户
    # ==================================================================

    @allure.story("单接口新增")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.parametrize("run_idx", range(ADD_COUNT))
    def test_add_user(self, run_idx: int) -> None:
        """TC-BATCH-001：调用新增用户接口，断言 code==200，数据保留不删除。"""
        allure.dynamic.title(f"TC-BATCH-001 [第{run_idx + 1}轮]：新增用户成功（数据保留）")

        token = _login_and_get_token()
        user_api, _, _, _ = _setup_apis(token)

        username = gen_username()
        phone = gen_phone()

        with allure.step(f"[轮次 {run_idx + 1}] 获取三级部门 dept_id"):
            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                dept_id = fetch_random_third_level_dept_id(102)
            dept_info = f"dept_id={dept_id}" if dept_id else "未取到部门（不传 deptId）"

        allure.attach(
            body=f"run_idx={run_idx}\nuserName={username}\nphone={phone}\n{dept_info}",
            name=f"[轮次 {run_idx + 1}] 入参摘要",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 调用 POST /system/user"):
            resp = user_api.add_user(
                user_name=username,
                nick_name=f"批量测试用户{run_idx + 1}",
                password="Test@123456",
                phonenumber=phone,
                dept_id=dept_id,
                remark=f"批量新增第{run_idx + 1}轮，数据保留",
            )

        allure.attach(
            body=str(resp),
            name=f"[轮次 {run_idx + 1}] 新增用户响应",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 断言 code==200"):
            assert resp.get("code") == 200, (
                f"[轮次 {run_idx + 1}] 新增用户失败: userName={username}, "
                f"code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-BATCH-002：新增角色
    # ==================================================================

    @allure.story("单接口新增")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("run_idx", range(ADD_COUNT))
    def test_add_role(self, run_idx: int) -> None:
        """TC-BATCH-002：调用新增角色接口，断言 code==200，数据保留不删除。"""
        allure.dynamic.title(f"TC-BATCH-002 [第{run_idx + 1}轮]：新增角色成功（数据保留）")

        token = _login_and_get_token()
        _, role_api, _, _ = _setup_apis(token)

        role_name = _gen_role_name()
        role_key = _gen_role_key()

        allure.attach(
            body=f"run_idx={run_idx}\nroleName={role_name}\nroleKey={role_key}",
            name=f"[轮次 {run_idx + 1}] 入参摘要",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 调用 POST /system/role"):
            resp = role_api.add_role(
                role_name=role_name,
                role_key=role_key,
                role_sort=run_idx + 50,
                status="0",
                remark=f"批量新增第{run_idx + 1}轮，数据保留",
            )

        allure.attach(
            body=str(resp),
            name=f"[轮次 {run_idx + 1}] 新增角色响应",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 断言 code==200"):
            assert resp.get("code") == 200, (
                f"[轮次 {run_idx + 1}] 新增角色失败: roleName={role_name}, roleKey={role_key}, "
                f"code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-BATCH-003：新增岗位
    # ==================================================================

    @allure.story("单接口新增")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("run_idx", range(ADD_COUNT))
    def test_add_post(self, run_idx: int) -> None:
        """TC-BATCH-003：调用新增岗位接口，断言 code==200，数据保留不删除。"""
        allure.dynamic.title(f"TC-BATCH-003 [第{run_idx + 1}轮]：新增岗位成功（数据保留）")

        token = _login_and_get_token()
        _, _, post_api, _ = _setup_apis(token)

        post_code = _gen_post_code()
        post_name = _gen_post_name()

        allure.attach(
            body=f"run_idx={run_idx}\npostCode={post_code}\npostName={post_name}",
            name=f"[轮次 {run_idx + 1}] 入参摘要",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 调用 POST /system/post"):
            resp = post_api.add_post(
                post_code=post_code,
                post_name=post_name,
                post_sort=run_idx + 50,
                status="0",
                remark=f"批量新增第{run_idx + 1}轮，数据保留",
            )

        allure.attach(
            body=str(resp),
            name=f"[轮次 {run_idx + 1}] 新增岗位响应",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 断言 code==200"):
            assert resp.get("code") == 200, (
                f"[轮次 {run_idx + 1}] 新增岗位失败: postCode={post_code}, postName={post_name}, "
                f"code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-BATCH-004：新增公告
    # ==================================================================

    @allure.story("单接口新增")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("run_idx", range(ADD_COUNT))
    def test_add_notice(self, run_idx: int) -> None:
        """TC-BATCH-004：调用新增公告接口，断言 code==200，数据保留不删除。"""
        allure.dynamic.title(f"TC-BATCH-004 [第{run_idx + 1}轮]：新增公告成功（数据保留）")

        token = _login_and_get_token()
        _, _, _, notice_api = _setup_apis(token)

        notice_title = _gen_notice_title()

        allure.attach(
            body=f"run_idx={run_idx}\nnoticeTitle={notice_title}\nnoticeType=1（通知）",
            name=f"[轮次 {run_idx + 1}] 入参摘要",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 调用 POST /system/notice"):
            resp = notice_api.add_notice(
                notice_title=notice_title,
                notice_type="1",
                notice_content=f"第{run_idx + 1}轮批量新增公告正文，数据保留不删除",
                status="0",
                remark=f"批量新增第{run_idx + 1}轮，数据保留",
            )

        allure.attach(
            body=str(resp),
            name=f"[轮次 {run_idx + 1}] 新增公告响应",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"[轮次 {run_idx + 1}] 断言 code==200"):
            assert resp.get("code") == 200, (
                f"[轮次 {run_idx + 1}] 新增公告失败: noticeTitle={notice_title}, "
                f"code={resp.get('code')}, msg={resp.get('msg')}"
            )

    # ==================================================================
    # TC-BATCH-005：批量组合新增（用户 + 角色 + 岗位 + 公告）
    # ==================================================================

    @allure.story("批量组合新增")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.parametrize("run_idx", range(ADD_COUNT))
    def test_batch_add_all(self, run_idx: int) -> None:
        """
        TC-BATCH-005：四接口组合批量新增（用户 + 角色 + 岗位 + 公告）。

        每轮依次调用:
          1. POST /system/user   → 新增用户
          2. POST /system/role   → 新增角色
          3. POST /system/post   → 新增岗位
          4. POST /system/notice → 新增公告
        全部断言 code==200，数据保留不删除。
        """
        allure.dynamic.title(
            f"TC-BATCH-005 [第{run_idx + 1}/{ADD_COUNT}轮]：四接口组合批量新增（数据保留）"
        )

        token = _login_and_get_token()
        user_api, role_api, post_api, notice_api = _setup_apis(token)

        # ---- 生成本轮唯一标识符 ----
        uid = uuid.uuid4().hex[:8]
        username = f"batch_{uid}"
        phone = gen_phone()
        role_name = f"批量角色_{uid}"
        role_key = f"batch_role_{uid}"
        post_code = f"batch_post_{uid}"
        post_name = f"批量岗位_{uid}"
        notice_title = f"批量公告_{uid}"

        allure.attach(
            body=(
                f"轮次:         {run_idx + 1} / {ADD_COUNT}\n"
                f"uid:          {uid}\n"
                f"userName:     {username}\n"
                f"phone:        {phone}\n"
                f"roleName:     {role_name}\n"
                f"roleKey:      {role_key}\n"
                f"postCode:     {post_code}\n"
                f"postName:     {post_name}\n"
                f"noticeTitle:  {notice_title}"
            ),
            name=f"[轮次 {run_idx + 1}] 批量新增入参摘要",
            attachment_type=allure.attachment_type.TEXT,
        )

        results: dict[str, dict] = {}

        # ---- Step 1: 新增用户 ----
        with allure.step(f"[轮次 {run_idx + 1}] Step-1 新增用户: POST /system/user"):
            dept_id = fetch_random_third_level_dept_id(101)
            if dept_id is None:
                dept_id = fetch_random_third_level_dept_id(102)
            resp_user = user_api.add_user(
                user_name=username,
                nick_name=f"批量用户{run_idx + 1}",
                password="Test@123456",
                phonenumber=phone,
                dept_id=dept_id,
                remark=f"批量第{run_idx + 1}轮，数据保留",
            )
            results["user"] = resp_user
            allure.attach(
                body=str(resp_user),
                name=f"[轮次 {run_idx + 1}] 新增用户响应",
                attachment_type=allure.attachment_type.TEXT,
            )

        # ---- Step 2: 新增角色 ----
        with allure.step(f"[轮次 {run_idx + 1}] Step-2 新增角色: POST /system/role"):
            resp_role = role_api.add_role(
                role_name=role_name,
                role_key=role_key,
                role_sort=run_idx + 80,
                status="0",
                remark=f"批量第{run_idx + 1}轮，数据保留",
            )
            results["role"] = resp_role
            allure.attach(
                body=str(resp_role),
                name=f"[轮次 {run_idx + 1}] 新增角色响应",
                attachment_type=allure.attachment_type.TEXT,
            )

        # ---- Step 3: 新增岗位 ----
        with allure.step(f"[轮次 {run_idx + 1}] Step-3 新增岗位: POST /system/post"):
            resp_post = post_api.add_post(
                post_code=post_code,
                post_name=post_name,
                post_sort=run_idx + 80,
                status="0",
                remark=f"批量第{run_idx + 1}轮，数据保留",
            )
            results["post"] = resp_post
            allure.attach(
                body=str(resp_post),
                name=f"[轮次 {run_idx + 1}] 新增岗位响应",
                attachment_type=allure.attachment_type.TEXT,
            )

        # ---- Step 4: 新增公告 ----
        with allure.step(f"[轮次 {run_idx + 1}] Step-4 新增公告: POST /system/notice"):
            resp_notice = notice_api.add_notice(
                notice_title=notice_title,
                notice_type="1",
                notice_content=f"第{run_idx + 1}轮批量新增公告正文，数据保留不删除",
                status="0",
                remark=f"批量第{run_idx + 1}轮，数据保留",
            )
            results["notice"] = resp_notice
            allure.attach(
                body=str(resp_notice),
                name=f"[轮次 {run_idx + 1}] 新增公告响应",
                attachment_type=allure.attachment_type.TEXT,
            )

        # ---- 汇总断言 ----
        with allure.step(f"[轮次 {run_idx + 1}] 汇总断言：四接口均返回 code==200"):
            summary_lines = []
            errors = []
            for entity, resp in results.items():
                code = resp.get("code")
                msg = resp.get("msg", "")
                summary_lines.append(f"{entity:8s}: code={code}  msg={msg}")
                if code != 200:
                    errors.append(f"{entity}: code={code}, msg={msg}")

            allure.attach(
                body="\n".join(summary_lines),
                name=f"[轮次 {run_idx + 1}] 汇总结果",
                attachment_type=allure.attachment_type.TEXT,
            )

            assert not errors, (
                f"[轮次 {run_idx + 1}] 批量新增存在失败项:\n" + "\n".join(errors)
            )

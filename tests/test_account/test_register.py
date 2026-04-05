"""
账户注册模块测试用例。

覆盖场景:
    TC-REG-001  正常注册（身份证）
    TC-REG-002  正常注册（护照）
    TC-REG-003  权限缺失拦截（预期 98880）
    TC-REG-004  重复注册互斥（预期 98882）
    TC-REG-005  数据驱动：多证件类型批量注册
"""
from __future__ import annotations

import pytest
import allure

from business.account_flows import AccountFlows
from core.request_wrapper import PermissionError, BusinessConflictError
from core.validator import Validator
from utils.db_client import DBClient
from utils.factory import IdentityFactory


@allure.epic("金融系统接口自动化")
@allure.feature("账户管理模块")
class TestAccountRegister:

    # ------------------------------------------------------------------
    # 正向用例
    # ------------------------------------------------------------------

    @allure.story("正常开户流程")
    @allure.title("TC-REG-001：使用身份证正常注册开户")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.account
    def test_register_with_id_card(self) -> None:
        """使用居民身份证完成账户注册，验证账户状态和 DB 数据落地。"""
        identity = IdentityFactory.gen_id_card_identity()
        flows = AccountFlows()

        with allure.step("附加测试身份信息"):
            allure.attach(
                body=str(identity),
                name="测试身份数据",
                attachment_type=allure.attachment_type.TEXT,
            )

        data = flows.full_register_flow(
            overrides={
                "cust_name": identity.name,
                "id_type": identity.id_type,
                "id_no": identity.id_no,
                "mobile": identity.mobile,
            }
        )

        with allure.step("断言响应字段：账户状态为 ACTIVE 或 PENDING"):
            assert data["status"] in ("ACTIVE", "PENDING"), f"账户状态异常: {data['status']}"
            assert data["cust_id"], "cust_id 不能为空"
            assert data["account_no"], "account_no 不能为空"

    @allure.story("正常开户流程")
    @allure.title("TC-REG-002：使用护照正常注册开户")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.account
    def test_register_with_passport(self) -> None:
        """使用护照完成账户注册，验证证件类型为 02 时字段逻辑正确。"""
        identity = IdentityFactory.gen_passport_identity()
        flows = AccountFlows()

        data = flows.full_register_flow(
            overrides={
                "cust_name": identity.name,
                "id_type": "02",
                "id_no": identity.id_no,
                "mobile": identity.mobile,
            }
        )

        assert data["account_no"], "护照注册返回的 account_no 不能为空"

    # ------------------------------------------------------------------
    # 负向用例：权限拦截
    # ------------------------------------------------------------------

    @allure.story("权限与安全拦截")
    @allure.title("TC-REG-003：无权限用户注册应返回 98880")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.account
    def test_register_without_permission(self) -> None:
        """使用无开户权限的账号登录后尝试注册，预期系统拦截并返回 98880。"""
        flows = AccountFlows()

        with allure.step("使用无权限账号登录"):
            flows.do_login(username="no_perm_user", password="Test@123456")

        with allure.step("预期注册被 98880 拦截"):
            with pytest.raises(PermissionError) as exc_info:
                flows.do_register()

        with allure.step("断言错误码和提示信息"):
            assert exc_info.value.biz_code == 98880
            assert "权限" in str(exc_info.value) or "permission" in str(exc_info.value).lower()

        with allure.step("断言 DB 无新增账户数据"):
            Validator.assert_db_not_exists(
                "SELECT 1 FROM t_account WHERE create_time > NOW() - INTERVAL 10 SECOND "
                "AND channel='API' LIMIT 1"
            )

    # ------------------------------------------------------------------
    # 负向用例：业务互斥
    # ------------------------------------------------------------------

    @allure.story("业务互斥拦截")
    @allure.title("TC-REG-004：已有账户的用户重复注册应返回 98882")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.account
    def test_register_duplicate(self) -> None:
        """同一证件号重复注册，预期触发业务互斥拦截（98882）。"""
        identity = IdentityFactory.gen_id_card_identity()
        flows = AccountFlows()

        overrides = {
            "cust_name": identity.name,
            "id_type": identity.id_type,
            "id_no": identity.id_no,
            "mobile": identity.mobile,
        }

        with allure.step("第一次注册，预期成功"):
            flows.full_register_flow(overrides=overrides)

        with allure.step("第二次注册相同证件号，预期 98882 业务互斥拦截"):
            flows2 = AccountFlows()
            flows2.do_login()
            with pytest.raises(BusinessConflictError) as exc_info:
                flows2.do_register(overrides=overrides)

        assert exc_info.value.biz_code == 98882

    # ------------------------------------------------------------------
    # 数据驱动用例
    # ------------------------------------------------------------------

    @allure.story("正常开户流程")
    @allure.title("TC-REG-005：数据驱动 - 多证件类型批量注册")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.account
    @pytest.mark.parametrize("id_type,id_no_tag", [
        ("01", "${gen_id_by_type(01)}"),
        ("02", "${gen_id_by_type(02)}"),
    ])
    def test_register_multi_id_types(self, id_type: str, id_no_tag: str) -> None:
        """使用不同证件类型分别注册，验证系统均能正常处理。"""
        from core.data_engine import DataEngine
        engine = DataEngine()
        id_no = engine._dispatch(id_no_tag.strip("${}"))

        flows = AccountFlows()
        data = flows.full_register_flow(
            overrides={"id_type": id_type, "id_no": id_no}
        )

        allure.attach(
            f"证件类型: {id_type}\n证件号: {id_no}\n账户号: {data.get('account_no')}",
            name="参数化数据记录",
            attachment_type=allure.attachment_type.TEXT,
        )
        assert data["account_no"], f"证件类型 {id_type} 注册失败，account_no 为空"

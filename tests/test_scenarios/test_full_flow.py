"""
跨模块复杂场景测试用例。

覆盖场景:
    TC-FLOW-001  完整开户 → 授信 → 放款 → 还款 链路
    TC-FLOW-002  开户后执行跨行转账，验证 MQ 异步状态流转
"""
from __future__ import annotations

import allure
import pytest

from business.loan_flows import LoanFlows
from business.account_flows import AccountFlows
from core.context import GlobalContext
from core.validator import Validator
from utils.factory import IdentityFactory


@allure.epic("金融系统接口自动化")
@allure.feature("长链路场景")
class TestFullFlow:

    @allure.story("放款闭环链路")
    @allure.title("TC-FLOW-001：完整放款闭环（开户→授信→放款→还款）")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.scenario
    @pytest.mark.slow
    def test_full_loan_flow(self) -> None:
        """
        验证金融系统核心放款链路的端到端闭环，
        覆盖开户、授信申请、放款到账（含 DB 异步轮询）、还款结清全过程。
        """
        loan_flows = LoanFlows()
        ctx = GlobalContext.instance()

        with allure.step("执行完整放款链路"):
            result = loan_flows.full_loan_flow(loan_amount=30000.0)

        with allure.step("断言最终还款状态"):
            assert result["status"] == "SUCCESS", f"还款状态异常: {result}"
            assert result["repay_amount"] == 30000.0

        with allure.step("断言 GlobalContext 关键变量均已填充"):
            assert ctx.get("cust_id"), "cust_id 未写入 GlobalContext"
            assert ctx.get("account_no"), "account_no 未写入 GlobalContext"
            assert ctx.get("apply_no"), "apply_no 未写入 GlobalContext"
            assert ctx.get("loan_order_no"), "loan_order_no 未写入 GlobalContext"

        allure.attach(
            body=str(ctx.snapshot()),
            name="链路执行后 GlobalContext 全量快照",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("跨行转账场景")
    @allure.title("TC-FLOW-002：开户后执行跨行转账，验证 MQ 异步状态流转")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.scenario
    def test_cross_bank_transfer_after_register(self) -> None:
        """
        开户成功后立即发起跨行转账，通过 DB 轮询断言 MQ 处理完成后
        订单状态更新为 SUCCESS。
        """
        from api.payment.transfer_api import TransferAPI

        identity = IdentityFactory.gen_id_card_identity()
        account_flows = AccountFlows()

        with allure.step("开户"):
            data = account_flows.full_register_flow(
                overrides={
                    "cust_name": identity.name,
                    "id_no": identity.id_no,
                    "mobile": identity.mobile,
                }
            )

        ctx = GlobalContext.instance()
        account_no = ctx.get_required("account_no")

        with allure.step("发起跨行转账"):
            transfer_api = TransferAPI()
            transfer_api.set_token(ctx.get_required("token"))
            resp = transfer_api.transfer(
                overrides={
                    "amount": 500.00,
                    "transfer_type": "CROSS_BANK",
                    "from_account_no": account_no,
                }
            )

        with allure.step("断言转账接口响应成功"):
            Validator.assert_success(resp)
            Validator.assert_schema(resp, "transfer_response")

        order_no = resp["data"]["order_no"]
        ctx.set("transfer_order_no", order_no)

        with allure.step(f"轮询等待 DB 订单 {order_no} 状态变为 SUCCESS"):
            Validator.assert_db_field(
                sql=f"SELECT status FROM t_transfer_order WHERE order_no='{order_no}'",
                expected="SUCCESS",
                timeout=60,
                interval=3.0,
            )

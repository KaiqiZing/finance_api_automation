"""
LoanFlows：放款/还款业务流编排。

典型长链路:
    开户 → 绑卡 → 授信申请 → 授信审批 → 放款 → 还款 → 结清

此模块负责:
1. 调用各阶段原子接口。
2. 通过 GlobalContext 传递 apply_no、loan_no 等核心业务变量。
3. 在 MQ 异步处理节点使用 Validator.assert_db_field() 轮询等待状态流转。
"""
from __future__ import annotations

from typing import Any

import allure

from api.payment.transfer_api import TransferAPI
from business.account_flows import AccountFlows
from core.context import GlobalContext
from core.validator import Validator
from utils.logger import logger


class LoanFlows:
    """放款业务流，供跨模块场景测试调用。"""

    def __init__(self) -> None:
        self._transfer_api = TransferAPI()
        self._account_flows = AccountFlows()
        self._ctx = GlobalContext.instance()
        self._validator = Validator()

    # ------------------------------------------------------------------
    # 阶段一：开户（复用 AccountFlows）
    # ------------------------------------------------------------------

    @allure.step("阶段一：完成开户")
    def step_open_account(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """执行完整开户流程，为后续放款做准备。"""
        return self._account_flows.full_register_flow(overrides=overrides)

    # ------------------------------------------------------------------
    # 阶段二：授信申请
    # ------------------------------------------------------------------

    @allure.step("阶段二：提交授信申请")
    def step_apply_credit(self, amount: float = 50000.0) -> str:
        """
        提交授信申请，返回申请单号。
        （此处为占位实现，需根据实际授信接口扩展）

        Args:
            amount: 授信金额。

        Returns:
            apply_no: 申请单号。
        """
        account_no = self._ctx.get_required("account_no")
        logger.info(f"[LoanFlows] 提交授信申请: account_no={account_no}, amount={amount}")
        apply_no = f"APPLY{account_no[-8:]}"
        self._ctx.set("apply_no", apply_no)
        self._ctx.set("credit_amount", amount)
        return apply_no

    # ------------------------------------------------------------------
    # 阶段三：放款
    # ------------------------------------------------------------------

    @allure.step("阶段三：执行放款")
    def step_disburse(self) -> dict[str, Any]:
        """
        执行放款（转账到账户），并轮询等待 DB 状态更新为 SUCCESS。

        Returns:
            转账响应 data 字典。
        """
        apply_no = self._ctx.get_required("apply_no")
        account_no = self._ctx.get_required("account_no")
        credit_amount = self._ctx.get("credit_amount", 50000.0)

        with allure.step("调用转账接口（放款）"):
            resp = self._transfer_api.transfer(
                overrides={
                    "amount": credit_amount,
                    "transfer_type": "INTRA_BANK",
                    "remark": f"授信放款 {apply_no}",
                }
            )

        with allure.step("断言转账业务成功"):
            self._validator.assert_success(resp)

        order_no = resp["data"]["order_no"]
        self._ctx.set("loan_order_no", order_no)

        with allure.step("轮询等待 DB 放款状态更新为 SUCCESS"):
            sql = f"SELECT status FROM t_transfer_order WHERE order_no='{order_no}'"
            self._validator.assert_db_field(sql, "SUCCESS", timeout=60)

        logger.info(f"[LoanFlows] 放款成功: order_no={order_no}")
        return resp["data"]

    # ------------------------------------------------------------------
    # 阶段四：还款
    # ------------------------------------------------------------------

    @allure.step("阶段四：执行还款")
    def step_repay(self, repay_amount: float | None = None) -> dict[str, Any]:
        """
        执行还款操作。
        （此处为占位实现，需根据实际还款接口扩展）

        Args:
            repay_amount: 还款金额，不传则全额还款。

        Returns:
            还款结果字典。
        """
        loan_order_no = self._ctx.get_required("loan_order_no")
        amount = repay_amount or self._ctx.get("credit_amount", 50000.0)
        logger.info(f"[LoanFlows] 执行还款: order_no={loan_order_no}, amount={amount}")
        self._ctx.set("repay_status", "SUCCESS")
        return {"loan_order_no": loan_order_no, "repay_amount": amount, "status": "SUCCESS"}

    # ------------------------------------------------------------------
    # 完整放款链路
    # ------------------------------------------------------------------

    @allure.step("完整放款链路：开户 → 授信 → 放款 → 还款")
    def full_loan_flow(self, loan_amount: float = 50000.0) -> dict[str, Any]:
        """
        执行完整放款闭环链路。

        Returns:
            最终还款结果字典。
        """
        self.step_open_account()
        self.step_apply_credit(amount=loan_amount)
        self.step_disburse()
        return self.step_repay()

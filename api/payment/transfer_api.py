"""
TransferAPI：转账原子接口。

对应模板: data/templates/payment/transfer.yaml
对应接口: POST /api/v1/payment/transfer
"""
from __future__ import annotations

from typing import Any

from api.base_api import BaseAPI


class TransferAPI(BaseAPI):
    """转账接口封装。"""

    _MODULE = "payment"
    _TEMPLATE = "transfer"

    def transfer(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        发起转账请求。

        Args:
            overrides: 字段覆盖，如 {"amount": 5000.00, "transfer_type": "CROSS_BANK"}。
                       支持直接覆盖 payload 顶层字段。

        Returns:
            接口响应 body 字典。
        """
        payload = self._build_payload(self._MODULE, self._TEMPLATE, overrides)
        return self._wrapper.post("/api/v1/payment/transfer", json=payload)

    def query_transfer_status(self, order_no: str) -> dict[str, Any]:
        """
        查询转账订单状态（轮询断言的前置查询接口）。

        Args:
            order_no: 转账订单号。

        Returns:
            接口响应 body 字典。
        """
        return self._wrapper.get(
            "/api/v1/payment/transfer/status",
            params={"order_no": order_no},
        )

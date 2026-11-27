"""成交记录领域服务：成交单的登记、确认、手续费计算、盈亏贡献。

跨模块数据流：
- 交易指令 → 成交记录(指令确认后自动生成成交记录，计算手续费)
- 成交记录 → 盈亏核算(按策略汇总已实现盈亏)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class TradeFillService(BaseModuleService):
    MODULE = "trade_fill"
    ENTITY = "成交单"
    OPERATION_TERM = "确认成交"
    ACTION_HOLD = None
    LIST_FIELDS = ["指令编号", "成交价格", "成交数量", "手续费率", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["指令编号", "成交价格", "成交数量"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认成交": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认成交":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                fee_info = self._calculate_fee(result[0])
                audit_service.log(action, str(entry.get("责任岗位", "结算员")),
                                f"成交记录{entry_id}已确认：{entry.get('成交价格')}×{entry.get('成交数量')}，手续费{fee_info['fee_amount']}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def _calculate_fee(self, fill: dict[str, Any]) -> dict[str, Any]:
        """计算成交手续费。"""
        try:
            price = float(fill.get("成交价格", 0))
            quantity = int(fill.get("成交数量", 0))
            rate = float(str(fill.get("手续费率", "0")))
        except (ValueError, TypeError):
            return {"fee_amount": 0, "price": 0, "quantity": 0, "rate": 0}
        fee_amount = round(price * quantity * rate, 4)
        return {"fee_amount": fee_amount, "price": price, "quantity": quantity, "rate": rate}

    def get_fills_for_instruct(self, instruct_no: str) -> list[dict[str, Any]]:
        """获取指定指令编号的所有成交记录。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("指令编号", "")) == instruct_no]

    def get_confirmed_fills(self) -> list[dict[str, Any]]:
        """获取所有已确认的成交记录(用于盈亏核算)。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") == "已确认"]

    def total_fee_summary(self) -> dict[str, Any]:
        """汇总所有已确认成交的手续费。"""
        confirmed = self.get_confirmed_fills()
        total_fee = 0.0
        for fill in confirmed:
            fee_info = self._calculate_fee(fill)
            total_fee += fee_info["fee_amount"]
        return {"total_fee": round(total_fee, 4), "fill_count": len(confirmed)}
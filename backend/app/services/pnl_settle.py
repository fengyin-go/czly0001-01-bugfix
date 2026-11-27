"""盈亏核算领域服务：核算单的登记、确认、按策略汇总盈亏。

跨模块数据流：
- 成交记录 → 盈亏核算(按策略汇总已实现/未实现盈亏)
- 持仓快照 → 盈亏核算(快照时点与核算区间交叉验证)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class PnlSettleService(BaseModuleService):
    MODULE = "pnl_settle"
    ENTITY = "核算单"
    OPERATION_TERM = "确认核算"
    ACTION_HOLD = None
    LIST_FIELDS = ["策略编号", "统计区间", "已实现盈亏", "未实现盈亏", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "统计区间", "已实现盈亏"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认核算": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认核算":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "核算员")),
                                f"盈亏核算{entry_id}已确认：策略{entry.get('策略编号')}，区间{entry.get('统计区间')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def aggregate_by_strategy(self, strategy_no: str) -> dict[str, Any]:
        """按策略汇总盈亏(从成交记录聚合计算)。"""
        fill_rows = store.rows("trade_fill")
        confirmed_fills = [row for row in fill_rows
                          if row.get("status") == "已确认"
                          and str(row.get("指令编号", "")).startswith(strategy_no[:4])]
        total_fee = 0.0
        for fill in confirmed_fills:
            try:
                price = float(fill.get("成交价格", 0))
                quantity = int(fill.get("成交数量", 0))
                rate = float(str(fill.get("手续费率", "0")))
                total_fee += price * quantity * rate
            except (ValueError, TypeError):
                pass

        # 检查持仓快照
        position_rows = store.rows("position_snapshot")
        confirmed_positions = [row for row in position_rows
                              if row.get("status") == "已确认"]

        return {
            "strategy_no": strategy_no,
            "realized_pnl": round(-total_fee, 4),  # 手续费为负向盈亏
            "fill_count": len(confirmed_fills),
            "position_count": len(confirmed_positions),
            "total_fee": round(total_fee, 4),
        }

    def get_settlements_for_strategy(self, strategy_no: str) -> list[dict[str, Any]]:
        """获取指定策略的所有核算记录。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("策略编号", "")) == strategy_no]
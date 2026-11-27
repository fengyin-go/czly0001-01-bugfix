"""信号订阅领域服务：信号单的登记、确认、自动生成交易指令。

跨模块数据流：
- 信号触发后 → 自动生成交易指令(写入 trade_instruct)
- 信号方向与触发价格 → 映射为委托方向和数量
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class SignalSubService(BaseModuleService):
    MODULE = "signal_sub"
    ENTITY = "信号单"
    OPERATION_TERM = "确认订阅"
    ACTION_HOLD = None
    LIST_FIELDS = ["策略编号", "信号方向", "触发价格", "有效期限", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "信号方向", "触发价格"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认订阅": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认订阅":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "信号员")),
                                f"信号{entry_id}已确认订阅：{entry.get('信号方向')} 触发价{entry.get('触发价格')}",
                                module_source=self.MODULE, entry_id=entry_id)
                # 信号确认后可触发交易指令
                from app.services.domain_coordinator import coordinator
                coordinator.trigger_trade_from_signal(result[0])
            return result
        return super().run_action(entry_id, action)

    def get_active_signals(self) -> list[dict[str, Any]]:
        """获取所有已确认且有效的信号。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") == "已确认"]

    def get_signals_for_strategy(self, strategy_no: str) -> list[dict[str, Any]]:
        """获取指定策略的信号订阅。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("策略编号", "")) == strategy_no]
"""交易指令领域服务：指令单的登记、发送、风控拦截、成交生成。

跨模块数据流：
- 风控规则 → 交易指令(action_hold 检查：发送指令时检查风控规则是否阻止)
- 信号订阅 → 交易指令(信号触发后自动生成交易指令)
- 交易指令 → 成交记录(指令确认后自动生成成交记录)
- 组合再平衡 → 交易指令(再平衡触发调仓指令)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class TradeInstructService(BaseModuleService):
    MODULE = "trade_instruct"
    ENTITY = "指令单"
    OPERATION_TERM = "发送指令"
    # action_hold: 发送指令前检查对应策略仍有已启用的风控规则在生效
    ACTION_HOLD = {
        "action": "发送指令",
        "source": "risk_rule",
        "match_field": "策略编号",
        "source_status": "已确认",
        "message": "对应策略仍有已启用的风控规则在生效，当前不能发送指令"
    }
    LIST_FIELDS = ["策略编号", "标的代码", "委托方向", "委托数量", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "标的代码", "委托方向"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"发送指令": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        """发送指令时增强风控检查并自动生成成交记录。"""
        if action == "发送指令":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            # 增强风控检查：action_hold + 维度检查
            from app.services.domain_coordinator import coordinator
            risk_check = coordinator.check_risk_for_trade(entry)
            if risk_check["status"] == "blocked":
                return None, risk_check["message"]
            # 执行基础动作(action_hold 检查仍在基类中执行)
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "交易员")),
                                f"交易指令{entry_id}已发送：{entry.get('标的代码')} {entry.get('委托方向')} {entry.get('委托数量')}",
                                module_source=self.MODULE, entry_id=entry_id)
                # 发送指令后自动生成成交记录
                coordinator.generate_trade_fill(result[0])
            return result
        return super().run_action(entry_id, action)

    def get_trades_for_strategy(self, strategy_no: str) -> list[dict[str, Any]]:
        """获取指定策略的所有交易指令。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("策略编号", "")) == strategy_no]

    def get_pending_trades(self) -> list[dict[str, Any]]:
        """获取所有待确认的交易指令。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") in ("草稿", "待确认")]
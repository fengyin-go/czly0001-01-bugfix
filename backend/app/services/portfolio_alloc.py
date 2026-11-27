"""组合配置领域服务：组合单的登记、确认，驱动再平衡决策。

跨模块数据流：
- 组合配置 → 再平衡执行 → 交易指令(组合再平衡触发调仓指令)
- 组合成员策略 → 影响分配比例的合法性校验
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class PortfolioAllocService(BaseModuleService):
    MODULE = "portfolio_alloc"
    ENTITY = "组合单"
    OPERATION_TERM = "确认组合"
    ACTION_HOLD = None
    LIST_FIELDS = ["组合名称", "成员策略", "分配比例", "再平衡周期", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["组合名称", "成员策略", "分配比例"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认组合": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认组合":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            # 校验成员策略是否都已确认
            members = str(entry.get("成员策略", "")).split(",")
            strategy_rows = store.rows("strategy_config")
            for member in members:
                member = member.strip()
                if not member:
                    continue
                found = False
                for srow in strategy_rows:
                    if str(srow.get("策略名称", "")) == member:
                        if srow.get("status") != "已确认":
                            return None, f"成员策略「{member}」状态为「{srow.get('status')}」，需先确认"
                        found = True
                        break
                if not found:
                    return None, f"成员策略「{member}」不存在"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "组合经理")),
                                f"组合{entry.get('组合名称')}已确认，成员策略{entry.get('成员策略')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_active_portfolios(self) -> list[dict[str, Any]]:
        """获取所有已确认的组合配置。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") == "已确认"]

    def get_portfolio_members(self, portfolio_name: str) -> list[dict[str, Any]]:
        """获取组合的成员策略详情。"""
        rows = store.rows(self.MODULE)
        portfolio = None
        for row in rows:
            if str(row.get("组合名称", "")) == portfolio_name:
                portfolio = row
                break
        if portfolio is None:
            return []
        members = str(portfolio.get("成员策略", "")).split(",")
        strategy_rows = store.rows("strategy_config")
        result = []
        for member in members:
            member = member.strip()
            if not member:
                continue
            for srow in strategy_rows:
                if str(srow.get("策略名称", "")) == member:
                    result.append(srow)
                    break
        return result
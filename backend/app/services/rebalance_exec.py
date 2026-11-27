"""再平衡执行领域服务：再平衡单的登记、执行，触发调仓指令。

跨模块数据流：
- 组合配置 → 再平衡执行(组合确认后可执行再平衡)
- 再平衡执行 → 交易指令(再平衡触发调仓指令)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class RebalanceExecService(BaseModuleService):
    MODULE = "rebalance_exec"
    ENTITY = "再平衡单"
    OPERATION_TERM = "执行再平衡"
    ACTION_HOLD = None
    LIST_FIELDS = ["组合编号", "执行时刻", "调整方向", "调整幅度", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["组合编号", "执行时刻", "调整方向"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"执行再平衡": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "执行再平衡":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            # 检查关联组合是否已确认
            combo_id = str(entry.get("组合编号", ""))
            portfolio_found = False
            for prow in store.rows("portfolio_alloc"):
                if str(prow.get("组合名称", "")) == combo_id:
                    if prow.get("status") != "已确认":
                        return None, f"关联组合「{combo_id}」状态为「{prow.get('status')}」，需先确认组合"
                    portfolio_found = True
                    break
            if not portfolio_found:
                return None, f"关联组合「{combo_id}」不存在"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "组合经理")),
                                f"再平衡{entry_id}已执行：组合{combo_id} {entry.get('调整方向')} {entry.get('调整幅度')}",
                                module_source=self.MODULE, entry_id=entry_id)
                # 再平衡执行后生成调仓指令
                from app.services.domain_coordinator import coordinator
                coordinator.execute_rebalance(result[0])
            return result
        return super().run_action(entry_id, action)

    def get_rebalances_for_portfolio(self, portfolio_name: str) -> list[dict[str, Any]]:
        """获取指定组合的所有再平衡记录。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("组合编号", "")) == portfolio_name]
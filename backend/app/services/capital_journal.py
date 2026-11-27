"""资金流水领域服务：流水单的登记、确认，与盈亏核算关联。

跨模块数据流：
- 资金流水 → 盈亏核算(流水变动影响账户净值)
- 成交记录 → 资金流水(成交引发的资金变动自动记录)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class CapitalJournalService(BaseModuleService):
    MODULE = "capital_journal"
    ENTITY = "流水单"
    OPERATION_TERM = "确认流水"
    ACTION_HOLD = None
    LIST_FIELDS = ["账户编号", "变动类型", "变动金额", "变动时刻", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["账户编号", "变动类型", "变动金额"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认流水": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认流水":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "财务员")),
                                f"资金流水{entry_id}已确认：{entry.get('变动类型')} {entry.get('变动金额')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_journals_for_account(self, account_no: str) -> list[dict[str, Any]]:
        """获取指定账户的所有资金流水。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("账户编号", "")) == account_no]

    def account_balance(self, account_no: str) -> dict[str, Any]:
        """计算指定账户的当前余额。"""
        journals = self.get_journals_for_account(account_no)
        total_in = 0.0
        total_out = 0.0
        for journal in journals:
            if journal.get("status") != "已确认":
                continue
            try:
                amount = float(journal.get("变动金额", 0))
            except (ValueError, TypeError):
                amount = 0
            var_type = str(journal.get("变动类型", ""))
            if "入" in var_type or "存入" in var_type or "盈利" in var_type:
                total_in += amount
            else:
                total_out += amount
        return {
            "account_no": account_no,
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "balance": round(total_in - total_out, 2),
            "journal_count": len(journals),
        }
"""策略评审领域服务：评审单的登记、确认，结论影响策略启用状态。

跨模块数据流：
- 策略评审 → 策略配置(评审结论影响策略启用/撤回状态)
- 评审结论为"不通过"/"否决" → 策略状态撤回
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class StrategyReviewService(BaseModuleService):
    MODULE = "strategy_review"
    ENTITY = "评审单"
    OPERATION_TERM = "确认评审"
    ACTION_HOLD = None
    LIST_FIELDS = ["策略编号", "实盘时长", "评审结论", "评审人员", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "实盘时长", "评审结论"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认评审": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认评审":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("评审人员", "评审员")),
                                f"策略评审{entry_id}已确认：结论{entry.get('评审结论')}",
                                module_source=self.MODULE, entry_id=entry_id)
                # 评审结论影响策略状态
                from app.services.domain_coordinator import coordinator
                coordinator.apply_review_to_strategy(result[0])
            return result
        return super().run_action(entry_id, action)

    def get_reviews_for_strategy(self, strategy_no: str) -> list[dict[str, Any]]:
        """获取指定策略的所有评审记录。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("策略编号", "")) == strategy_no]

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        """获取待评审的记录。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") in ("草稿", "待确认")]
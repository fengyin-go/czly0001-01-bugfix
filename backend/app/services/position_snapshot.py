"""持仓快照领域服务：持仓单的登记、确认，与盈亏核算区间交叉验证。

跨模块数据流：
- 持仓快照 → 盈亏核算(快照时点与核算区间交叉验证)
- 持仓数据 → 风控规则(检查卖出方向是否有足够持仓)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class PositionSnapshotService(BaseModuleService):
    MODULE = "position_snapshot"
    ENTITY = "持仓单"
    OPERATION_TERM = "确认快照"
    ACTION_HOLD = None
    LIST_FIELDS = ["标的代码", "持有数量", "成本均价", "快照时刻", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["标的代码", "持有数量", "成本均价"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认快照": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认快照":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "持仓管理员")),
                                f"持仓快照{entry_id}已确认：{entry.get('标的代码')} {entry.get('持有数量')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_position_for_symbol(self, symbol: str) -> dict[str, Any] | None:
        """获取指定标的的已确认持仓。"""
        rows = store.rows(self.MODULE)
        for row in rows:
            if str(row.get("标的代码", "")) == symbol and row.get("status") == "已确认":
                return row
        return None

    def validate_settle_interval(self, entry_id: int,
                                  interval_start: str, interval_end: str) -> dict[str, Any]:
        """验证持仓快照时点是否在核算区间内。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"status": "not_found"}
        snapshot_time = str(entry.get("快照时刻", ""))
        from app.services.domain_coordinator import coordinator
        return coordinator.cross_validate_snapshot_settle(entry, f"{interval_start} ~ {interval_end}")
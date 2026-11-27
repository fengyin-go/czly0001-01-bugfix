"""行情快照领域服务：行情单的登记、确认，价格触及阈值时生成预警。

跨模块数据流：
- 行情快照 → 预警派发(价格触及风控阈值时生成预警)
- 行情数据 → 风控规则(为规则阈值提供实时参考)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class MarketSnapshotService(BaseModuleService):
    MODULE = "market_snapshot"
    ENTITY = "行情单"
    OPERATION_TERM = "确认行情"
    ACTION_HOLD = None
    LIST_FIELDS = ["标的代码", "最新价格", "二十四小时涨跌", "成交额", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["标的代码", "最新价格", "二十四小时涨跌"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认行情": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认行情":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "行情管理员")),
                                f"行情{entry_id}已确认：{entry.get('标的代码')} 价格{entry.get('最新价格')}",
                                module_source=self.MODULE, entry_id=entry_id)
                # 检查是否触发预警
                from app.services.domain_coordinator import coordinator
                coordinator.check_threshold_and_alert(result[0])
            return result
        return super().run_action(entry_id, action)

    def get_snapshots_for_symbol(self, symbol: str) -> list[dict[str, Any]]:
        """获取指定标的的所有行情快照。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("标的代码", "")) == symbol]

    def get_latest_price(self, symbol: str) -> float | None:
        """获取指定标的最新确认价格。"""
        snapshots = self.get_snapshots_for_symbol(symbol)
        confirmed = [s for s in snapshots if s.get("status") == "已确认"]
        if not confirmed:
            return None
        try:
            return float(confirmed[-1].get("最新价格", 0))
        except (ValueError, TypeError):
            return None
"""预警派发领域服务：预警单的生成、签收、关联规则溯源。

跨模块数据流：
- 行情快照 → 预警派发(价格触及风控阈值时自动生成预警)
- 风控规则 → 预警派发(预警关联的具体规则类型和阈值)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class AlertDispatchService(BaseModuleService):
    MODULE = "alert_dispatch"
    ENTITY = "预警单"
    OPERATION_TERM = "签收预警"
    ACTION_HOLD = None
    LIST_FIELDS = ["预警类型", "触发规则", "当前数值", "接收人员", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["预警类型", "触发规则", "当前数值"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"签收预警": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "签收预警":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("接收人员", "风控员")),
                                f"预警{entry_id}已签收：{entry.get('预警类型')} {entry.get('当前数值')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_unacknowledged_alerts(self) -> list[dict[str, Any]]:
        """获取所有未签收的预警。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") in ("草稿", "待确认")]

    def get_alerts_by_type(self, alert_type: str) -> list[dict[str, Any]]:
        """按预警类型查询。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if alert_type in str(row.get("预警类型", ""))]

    def alert_statistics(self) -> dict[str, Any]:
        """预警统计分析。"""
        rows = store.rows(self.MODULE)
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for row in rows:
            atype = str(row.get("预警类型", "未知"))
            astatus = str(row.get("status", "未知"))
            by_type[atype] = by_type.get(atype, 0) + 1
            by_status[astatus] = by_status.get(astatus, 0) + 1
        return {
            "total": len(rows),
            "by_type": by_type,
            "by_status": by_status,
            "unacknowledged": sum(1 for r in rows if r.get("status") in ("草稿", "待确认")),
        }
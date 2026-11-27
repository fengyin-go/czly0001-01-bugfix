"""操作审计领域服务：审计单的登记、归档、查询。

跨模块数据流：
- 所有关键操作 → 操作审计(自动生成审计记录)
- 通过 audit_trail.AuditTrail.log() 供各模块调用
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class OperationAuditService(BaseModuleService):
    MODULE = "operation_audit"
    ENTITY = "审计单"
    OPERATION_TERM = "归档审计"
    ACTION_HOLD = None
    LIST_FIELDS = ["操作类型", "操作人员", "操作内容", "操作时刻", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["操作类型", "操作人员", "操作内容"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"归档审计": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "归档审计":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("操作人员", "系统")),
                                f"审计记录{entry_id}已归档",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_audits_by_action(self, action_type: str) -> list[dict[str, Any]]:
        """按操作类型查询审计记录。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("操作类型", "")) == action_type]

    def get_audits_by_operator(self, operator: str) -> list[dict[str, Any]]:
        """按操作人员查询审计记录。"""
        return audit_service.query_by_operator(operator)

    def timeline(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取审计时间线(最近的操作记录)。"""
        rows = store.rows(self.MODULE)
        sorted_rows = sorted(rows, key=lambda r: str(r.get("操作时刻", "")), reverse=True)
        return sorted_rows[:limit]

    def daily_summary(self) -> dict[str, Any]:
        """审计操作日统计。"""
        rows = store.rows(self.MODULE)
        by_type: dict[str, int] = {}
        by_operator: dict[str, int] = {}
        for row in rows:
            atype = str(row.get("操作类型", "未知"))
            op = str(row.get("操作人员", "未知"))
            by_type[atype] = by_type.get(atype, 0) + 1
            by_operator[op] = by_operator.get(op, 0) + 1
        return {
            "total": len(rows),
            "by_type": by_type,
            "by_operator": by_operator,
            "top_actions": sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10],
        }
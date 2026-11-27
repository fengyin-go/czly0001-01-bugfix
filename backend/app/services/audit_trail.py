"""操作审计服务：自动记录关键操作的审计日志。

所有跨模块操作（确认策略、启动回测、发送指令等）都自动生成审计记录。
"""
from __future__ import annotations

import datetime
from typing import Any

from app.store import store


class AuditTrail:
    """审计日志服务，记录关键操作的完整链路。"""

    def log(self, action_type: str, operator: str, content: str,
            module_source: str = "", entry_id: int = 0) -> dict[str, Any] | None:
        """记录一条审计日志。

        Args:
            action_type: 操作类型（如 '确认策略'、'启动回测'、'发送指令'）
            operator: 操作人员
            content: 操作内容描述
            module_source: 来源模块
            entry_id: 关联的业务条目 ID
        """
        rows = store.rows("operation_audit")
        new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "id": new_id,
            "操作类型": action_type,
            "操作人员": operator,
            "操作内容": content,
            "操作时刻": now,
            "责任岗位": operator,
            "登记批号": f"AUD-{new_id:04d}",
            "业务版本": "v1.0",
            "补充说明": f"来源模块: {module_source}, 关联条目: {entry_id}",
            "status": "草稿",
            "pending": True,
            "abnormal": False,
            "_module_source": module_source,
            "_entry_id": entry_id,
        }
        rows.append(record)
        return record

    def query_by_module(self, module_name: str) -> list[dict[str, Any]]:
        """按来源模块查询审计记录。"""
        rows = store.rows("operation_audit")
        return [row for row in rows
                if str(row.get("_module_source", "")) == module_name]

    def query_by_operator(self, operator: str) -> list[dict[str, Any]]:
        """按操作人员查询审计记录。"""
        rows = store.rows("operation_audit")
        return [row for row in rows
                if str(row.get("操作人员", "")) == operator]

    def query_by_timerange(self, start: str, end: str) -> list[dict[str, Any]]:
        """按时间范围查询审计记录。"""
        rows = store.rows("operation_audit")
        return [row for row in rows
                if start <= str(row.get("操作时刻", "")) <= end]

    def recent_audits(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取最近的审计记录。"""
        rows = store.rows("operation_audit")
        sorted_rows = sorted(rows, key=lambda r: str(r.get("操作时刻", "")), reverse=True)
        return sorted_rows[:limit]

    def module_audit_summary(self) -> dict[str, int]:
        """按模块汇总审计记录数。"""
        rows = store.rows("operation_audit")
        summary: dict[str, int] = {}
        for row in rows:
            module = str(row.get("_module_source", "unknown"))
            summary[module] = summary.get(module, 0) + 1
        return summary


audit_service = AuditTrail()
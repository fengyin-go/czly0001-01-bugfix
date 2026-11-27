"""回测报告领域服务：报告单的登记、确认、指标提取供风控参考。

跨模块数据流：
- 报告确认 → 提取年化收益、最大回撤、夏普比率供风控规则设定阈值
- 报告指标 → 风控员根据报告设定规则(action_hold 的数据源)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class BacktestReportService(BaseModuleService):
    MODULE = "backtest_report"
    ENTITY = "报告单"
    OPERATION_TERM = "确认报告"
    ACTION_HOLD = None
    LIST_FIELDS = ["回测编号", "年化收益", "最大回撤", "夏普比率", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["回测编号", "年化收益", "最大回撤"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认报告": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "确认报告":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "分析员")),
                                f"回测报告{entry_id}已确认，回测编号{entry.get('回测编号')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_report_metrics(self, entry_id: int) -> dict[str, Any]:
        """提取报告的量化指标供风控参考。"""
        report = store.find(self.MODULE, entry_id)
        if report is None:
            return {"status": "not_found"}
        return {
            "status": "ok",
            "backtest_id": str(report.get("回测编号", "")),
            "annual_return": str(report.get("年化收益", "")),
            "max_drawdown": str(report.get("最大回撤", "")),
            "sharpe_ratio": str(report.get("夏普比率", "")),
            "report_status": str(report.get("status", "")),
        }

    def get_reports_for_backtest(self, backtest_id: str) -> list[dict[str, Any]]:
        """获取指定回测编号的所有报告。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("回测编号", "")) == backtest_id]
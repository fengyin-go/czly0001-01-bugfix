"""风控规则领域服务：风控单的登记、启用、交易指令拦截。

跨模块数据流：
- 回测报告 → 风控规则(风控员根据报告指标设定阈值)
- 风控规则 → 交易指令(发送指令时检查风控规则是否阻止，action_hold)
- 行情快照 → 风控规则(价格触及阈值触发规则)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class RiskRuleService(BaseModuleService):
    MODULE = "risk_rule"
    ENTITY = "风控单"
    OPERATION_TERM = "启用规则"
    ACTION_HOLD = None
    LIST_FIELDS = ["策略编号", "规则类型", "阈值上限", "适用策略", "生效范围", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "规则类型", "阈值上限"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"启用规则": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "启用规则":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "风控员")),
                                f"风控规则{entry_id}已启用：{entry.get('规则类型')}，阈值{entry.get('阈值上限')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_active_rules_for_strategy(self, strategy_no: str) -> list[dict[str, Any]]:
        """获取指定策略的已启用风控规则。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows
                if str(row.get("策略编号", "")) == strategy_no
                and row.get("status") == "已确认"]

    def check_trade_block(self, strategy_no: str, direction: str) -> dict[str, Any]:
        """检查交易是否被风控规则阻止(增强版，供 domain_coordinator 使用)。"""
        active_rules = self.get_active_rules_for_strategy(strategy_no)
        if not active_rules:
            return {"status": "ok", "message": "无风控规则拦截"}
        blocking = []
        for rule in active_rules:
            rule_type = str(rule.get("规则类型", ""))
            if "禁止" in rule_type or direction in rule_type:
                blocking.append({
                    "rule_id": rule.get("id"),
                    "rule_type": rule_type,
                    "threshold": str(rule.get("阈值上限", "")),
                })
        if blocking:
            return {"status": "blocked", "blocking_rules": blocking,
                    "message": f"{len(blocking)}条风控规则拦截该交易"}
        return {"status": "ok"}

    def get_rules_with_report_context(self) -> list[dict[str, Any]]:
        """获取风控规则及其关联的回测报告指标。"""
        rows = store.rows(self.MODULE)
        result = []
        for rule in rows:
            strategy_no = str(rule.get("策略编号", ""))
            report_rows = store.rows("backtest_report")
            reports = [r for r in report_rows
                      if str(r.get("回测编号", "")).startswith(strategy_no[:4])]
            result.append({
                "rule": rule,
                "related_reports": len(reports),
                "report_metrics": [{
                    "id": r.get("id"),
                    "annual_return": str(r.get("年化收益", "")),
                    "max_drawdown": str(r.get("最大回撤", "")),
                    "sharpe": str(r.get("夏普比率", "")),
                } for r in reports if r.get("status") == "已确认"],
            })
        return result
"""预警引擎：行情阈值监控和预警生成。

处理行情价格与风控阈值的比对，生成和派发预警。
"""
from __future__ import annotations

from typing import Any

from app.store import store
from app.services.audit_trail import audit_service


class AlertEngine:
    """预警引擎。"""

    def evaluate_market_price(self, symbol: str, price: float) -> list[dict[str, Any]]:
        """评估行情价格是否触发风控预警。"""
        alerts = []
        risk_rules = store.rows("risk_rule")
        active_rules = [r for r in risk_rules if r.get("status") == "已确认"]

        for rule in active_rules:
            rule_type = str(rule.get("规则类型", ""))
            try:
                threshold = float(str(rule.get("阈值上限", "Inf")))
            except (ValueError, TypeError):
                continue

            if self._is_threshold_breached(rule_type, price, threshold):
                alert = self._create_alert(symbol, price, rule, rule_type, threshold)
                alerts.append(alert)

        return alerts

    def _is_threshold_breached(self, rule_type: str, price: float, threshold: float) -> bool:
        """判断价格是否触及阈值。"""
        if "价格" in rule_type or "突破" in rule_type:
            return price >= threshold
        if "回撤" in rule_type:
            return price <= threshold  # 回撤是负向的
        return price >= threshold

    def _create_alert(self, symbol: str, price: float,
                       rule: dict[str, Any], rule_type: str,
                       threshold: float) -> dict[str, Any]:
        """生成预警记录。"""
        rows = store.rows("alert_dispatch")
        new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        alert = {
            "id": new_id,
            "预警类型": f"价格{rule_type}预警",
            "触发规则": str(rule.get("策略编号", "")),
            "当前数值": str(price),
            "接收人员": "风控员-系统自动",
            "责任岗位": "预警引擎",
            "登记批号": f"ALERT-{new_id:04d}",
            "业务版本": "v1.0",
            "补充说明": f"标的{symbol}价格{price}触及{rule_type}阈值{threshold}",
            "status": "草稿",
            "pending": True,
            "abnormal": True,
        }
        rows.append(alert)
        audit_service.log("预警自动生成", "预警引擎",
                        f"标的{symbol}触发{rule_type}预警，价格{price}>={threshold}")
        return alert

    def batch_evaluate(self, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """批量评估多个行情快照。"""
        all_alerts = []
        for snap in snapshots:
            symbol = str(snap.get("标的代码", ""))
            try:
                price = float(snap.get("最新价格", 0))
            except (ValueError, TypeError):
                continue
            alerts = self.evaluate_market_price(symbol, price)
            all_alerts.extend(alerts)
        return all_alerts

    def get_alert_count_by_severity(self) -> dict[str, int]:
        """按严重程度统计预警。"""
        rows = store.rows("alert_dispatch")
        by_type: dict[str, int] = {}
        for row in rows:
            atype = str(row.get("预警类型", "未知"))
            by_type[atype] = by_type.get(atype, 0) + 1
        return by_type


class ReconEngine:
    """持仓对账引擎。"""

    def reconcile_positions(self, symbol: str) -> dict[str, Any]:
        """对账指定标的的持仓数量与成交数量。"""
        positions = store.rows("position_snapshot")
        fills = store.rows("trade_fill")

        pos_qty = 0
        for pos in positions:
            if str(pos.get("标的代码", "")) == symbol and pos.get("status") == "已确认":
                try:
                    pos_qty += int(pos.get("持有数量", 0))
                except (ValueError, TypeError):
                    pass

        fill_qty = 0
        for fill in fills:
            if fill.get("status") == "已确认":
                try:
                    fill_qty += int(fill.get("成交数量", 0))
                except (ValueError, TypeError):
                    pass

        diff = pos_qty - fill_qty
        return {
            "symbol": symbol,
            "position_quantity": pos_qty,
            "fill_quantity": fill_qty,
            "difference": diff,
            "is_balanced": diff == 0,
            "status": "ok" if diff == 0 else "imbalance",
        }


alert_engine = AlertEngine()
recon_engine = ReconEngine()
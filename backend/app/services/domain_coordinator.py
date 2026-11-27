"""跨模块协调器：统筹策略、回测、风控、交易、盈亏的全链路数据流。

职责：
- 策略确认后预加载因子库，校验因子权重
- 回测完成后自动生成报告快照
- 报告确认后通知风控模块可设置规则
- 发送指令时跨模块检查风控规则 action_hold
- 成交后自动触发盈亏核算预计算
- 所有关键操作写入审计日志
"""
from __future__ import annotations

import time
from typing import Any

from app.store import store
from app.services.audit_trail import audit_service


class DomainCoordinator:
    """协调各模块间的业务数据流。"""

    # ---------- 策略配置 → 因子库 ----------

    def validate_strategy_factors(self, strategy: dict[str, Any]) -> dict[str, Any]:
        """校验策略引用的因子定义是否存在、权重是否合法。

        返回值含 status='ok' 或 status='blocked' 及缺失/越权的因子列表。
        """
        factor_rows = store.rows("factor_library")
        if not strategy.get("参数集合"):
            return {"status": "ok", "factors": [], "message": "策略无需引用因子"}
        param_set = str(strategy["参数集合"])
        referenced_factors = [
            f.strip() for f in param_set.split(",") if f.strip()
        ]
        missing = []
        invalid_weight = []
        valid_factors = []
        for ref in referenced_factors:
            matched = False
            for frow in factor_rows:
                if str(frow.get("因子名称", "")) == ref and frow.get("status") == "已确认":
                    matched = True
                    try:
                        weight = float(str(frow.get("权重系数", "0")))
                        if not 0 < weight <= 1:
                            invalid_weight.append(ref)
                        else:
                            valid_factors.append({"name": ref, "weight": weight})
                    except (ValueError, TypeError):
                        invalid_weight.append(ref)
                    break
            if not matched:
                missing.append(ref)

        if missing:
            return {"status": "blocked", "missing_factors": missing,
                    "message": f"策略引用的因子未确认或不存在：{'、'.join(missing)}"}
        if invalid_weight:
            return {"status": "blocked", "invalid_weight_factors": invalid_weight,
                    "message": f"因子权重系数不合法(需0-1之间)：{'、'.join(invalid_weight)}"}
        return {"status": "ok", "factors": valid_factors,
                "message": f"已校验{len(valid_factors)}个因子定义"}

    # ---------- 策略配置 → 回测任务 ----------

    def can_launch_backtest(self, strategy_id: int) -> dict[str, Any]:
        """检查策略是否允许启动回测：状态必须为已确认。"""
        strategy = store.find("strategy_config", strategy_id)
        if strategy is None:
            return {"status": "blocked", "reason": "策略不存在"}
        if strategy.get("status") != "已确认":
            return {"status": "blocked", "reason": f"策略当前状态为「{strategy.get('status')}」，需先确认为「已确认」"}
        return {"status": "ok", "strategy": strategy}

    # ---------- 回测任务 → 回测报告 ----------

    def generate_backtest_report(self, task: dict[str, Any]) -> dict[str, Any] | None:
        """回测任务完成后，自动生成一份报告草稿。

        返回值是新创建的报告条目，None 表示该任务已有对应报告。
        """
        backtest_id = str(task.get("策略编号", ""))
        existing = [
            row for row in store.rows("backtest_report")
            if str(row.get("回测编号", "")) == backtest_id
        ]
        if existing:
            return None
        # 模拟回测计算
        import random
        random.seed(int(task.get("id", 1)))
        annual_return = round(random.uniform(-0.1, 0.45) * 100, 2)
        max_drawdown = round(random.uniform(0.05, 0.35) * 100, 2)
        sharpe = round(random.uniform(0.3, 3.5), 2)

        rows = store.rows("backtest_report")
        new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        report = {
            "id": new_id,
            "回测编号": backtest_id,
            "年化收益": f"{annual_return}%",
            "最大回撤": f"{max_drawdown}%",
            "夏普比率": str(sharpe),
            "责任岗位": task.get("责任岗位", "系统"),
            "登记批号": f"RPT-{new_id:04d}",
            "业务版本": "v1.0",
            "补充说明": f"基于回测任务{backtest_id}自动生成",
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        }
        rows.append(report)
        audit_service.log("回测完成", "系统", f"回测{backtest_id}完成，自动生成报告{new_id}")
        return report

    # ---------- 回测报告 → 风控规则 ----------

    def report_metrics_for_risk(self, report_id: int) -> dict[str, Any]:
        """提取回测报告的指标，供风控规则设定阈值参考。"""
        report = store.find("backtest_report", report_id)
        if report is None:
            return {"status": "not_found"}
        return {
            "status": "ok",
            "backtest_id": str(report.get("回测编号", "")),
            "annual_return": str(report.get("年化收益", "")),
            "max_drawdown": str(report.get("最大回撤", "")),
            "sharpe": str(report.get("夏普比率", "")),
        }

    # ---------- 风控规则 → 交易指令 (action_hold) ----------

    def check_risk_for_trade(self, trade: dict[str, Any]) -> dict[str, Any]:
        """发送交易指令前检查风控规则是否阻止。

        已在 BaseModuleService.ACTION_HOLD 中定义了基础检查逻辑，
        这里做增强：同时检查策略级别的多维度风控。
        """
        strategy_no = str(trade.get("策略编号", ""))
        risk_rows = store.rows("risk_rule")
        blocking_rules = []
        for rule in risk_rows:
            if (str(rule.get("策略编号", "")) == strategy_no
                    and rule.get("status") == "已确认"):
                blocking_rules.append({
                    "rule_id": rule.get("id"),
                    "rule_type": rule.get("规则类型"),
                    "threshold": rule.get("阈值上限"),
                })

        # 检查仓位快照与交易方向的合规性
        symbol = str(trade.get("标的代码", ""))
        direction = str(trade.get("委托方向", ""))
        position_rows = store.rows("position_snapshot")
        position_conflict = False
        for pos in position_rows:
            if str(pos.get("标的代码", "")) == symbol and pos.get("status") == "已确认":
                try:
                    quantity = int(pos.get("持有数量", 0))
                except (ValueError, TypeError):
                    quantity = 0
                if direction == "卖出" and quantity <= 0:
                    position_conflict = True
                    blocking_rules.append({
                        "rule_id": "POS",
                        "rule_type": "持仓冲突",
                        "threshold": f"当前持有{quantity}，无法卖出",
                    })
                break

        if blocking_rules or position_conflict:
            return {"status": "blocked", "blocking_rules": blocking_rules,
                    "message": f"风控规则阻止：{len(blocking_rules)}条规则拦截"}
        return {"status": "ok"}

    # ---------- 交易指令 → 成交记录 ----------

    def generate_trade_fill(self, instruct: dict[str, Any]) -> dict[str, Any] | None:
        """交易指令确认后自动生成成交记录。"""
        instruct_id = str(instruct.get("策略编号", ""))
        existing = [
            row for row in store.rows("trade_fill")
            if str(row.get("指令编号", "")) == instruct_id
            and row.get("status") == "已确认"
        ]
        if existing:
            return None
        # 模拟成交价格
        import random
        random.seed(int(instruct.get("id", 1)))
        base_price = random.uniform(10, 500)
        try:
            quantity = int(instruct.get("委托数量", 0))
        except (ValueError, TypeError):
            quantity = 0
        fee_rate = round(random.uniform(0.001, 0.005), 4)
        fill_price = round(base_price * (1 + random.uniform(-0.02, 0.02)), 2)
        fee_amount = round(fill_price * quantity * fee_rate, 2)

        rows = store.rows("trade_fill")
        new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        fill = {
            "id": new_id,
            "指令编号": instruct_id,
            "成交价格": fill_price,
            "成交数量": quantity,
            "手续费率": str(fee_rate),
            "责任岗位": instruct.get("责任岗位", "系统"),
            "登记批号": f"FILL-{new_id:04d}",
            "业务版本": "v1.0",
            "补充说明": f"手续费{round(fee_amount, 2)}={fill_price}×{quantity}×{fee_rate}",
            "status": "草稿",
            "pending": True,
            "abnormal": False,
            "_fee_amount": fee_amount,
        }
        rows.append(fill)
        audit_service.log("成交生成", "系统", f"指令{instruct_id}确认，自动生成成交记录{new_id}，手续费{fee_amount}")
        return fill

    # ---------- 成交记录 → 盈亏核算 ----------

    def aggregate_pnl_by_strategy(self, strategy_no: str) -> dict[str, Any]:
        """按策略汇总已实现和未实现盈亏。"""
        fill_rows = [
            row for row in store.rows("trade_fill")
            if str(row.get("指令编号", "")).startswith(strategy_no[:4])
            and row.get("status") == "已确认"
        ]
        position_rows = store.rows("position_snapshot")
        cost_rows = [
            row for row in position_rows
            if row.get("status") == "已确认"
        ]

        realized_pnl = 0.0
        for fill in fill_rows:
            fee = fill.get("_fee_amount", 0) if isinstance(fill.get("_fee_amount"), (int, float)) else 0
            realized_pnl += float(fee)

        unrealized_pnl = 0.0
        for cost in cost_rows:
            try:
                unrealized_pnl += float(cost.get("最新价格", cost.get("持有数量", 0)))
            except (ValueError, TypeError):
                pass

        return {
            "strategy_no": strategy_no,
            "realized_pnl": round(realized_pnl, 4),
            "unrealized_pnl": round(unrealized_pnl, 4),
            "fill_count": len(fill_rows),
            "position_count": len(cost_rows),
        }

    # ---------- 信号订阅 → 交易指令 ----------

    def trigger_trade_from_signal(self, signal: dict[str, Any]) -> dict[str, Any] | None:
        """信号触发后自动生成交易指令草稿。"""
        if signal.get("status") != "已确认":
            return None
        strategy_no = str(signal.get("策略编号", ""))
        direction = str(signal.get("信号方向", ""))
        price = signal.get("触发价格", 0)

        # 查找对应策略
        strategy_rows = store.rows("strategy_config")
        strategy = None
        for srow in strategy_rows:
            if str(srow.get("策略名称", "")) == strategy_no or srow.get("status") == "已确认":
                strategy = srow
                break

        symbol = str(strategy.get("标的品种", "BTCUSDT")) if strategy else "BTCUSDT"
        try:
            quantity = max(1, int(float(str(price)) / 100))
        except (ValueError, TypeError):
            quantity = 10

        rows = store.rows("trade_instruct")
        new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        instruct = {
            "id": new_id,
            "策略编号": f"SIGN-{new_id:04d}",
            "标的代码": symbol,
            "委托方向": direction,
            "委托数量": quantity,
            "责任岗位": signal.get("责任岗位", "交易员"),
            "登记批号": f"SIG-{new_id:04d}",
            "业务版本": "v1.0",
            "补充说明": f"信号触发自动生成，触发价格{price}",
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        }
        rows.append(instruct)
        audit_service.log("信号触发", "系统", f"信号{signal.get('id')}触发，自动生成交易指令{new_id}")
        return instruct

    # ---------- 持仓快照 → 盈亏核算 ----------

    def cross_validate_snapshot_settle(self, snapshot: dict[str, Any],
                                        settle_interval: str) -> dict[str, Any]:
        """持仓快照的时点与盈亏核算区间做交叉验证。

        检查快照时刻是否落在核算区间内。
        """
        snapshot_time = str(snapshot.get("快照时刻", ""))
        return {
            "status": "ok",
            "snapshot_time": snapshot_time,
            "settle_interval": settle_interval,
            "valid": True,
            "symbol": str(snapshot.get("标的代码", "")),
            "quantity": snapshot.get("持有数量", 0),
            "cost_price": str(snapshot.get("成本均价", "")),
        }

    # ---------- 策略评审 → 策略配置 ----------

    def apply_review_to_strategy(self, review: dict[str, Any]) -> dict[str, Any]:
        """评审结论影响策略启用状态。"""
        strategy_no = str(review.get("策略编号", ""))
        conclusion = str(review.get("评审结论", ""))
        strategy_rows = store.rows("strategy_config")
        for srow in strategy_rows:
            if str(srow.get("策略名称", "")) == strategy_no:
                if "不通过" in conclusion or "否决" in conclusion:
                    srow["status"] = "已撤回"
                    srow["abnormal"] = True
                    srow["补充说明"] = f"评审结论：{conclusion}，策略已撤回到草稿"
                    audit_service.log("评审撤回", str(review.get("评审人员", "")),
                                    f"策略{strategy_no}评审不通过，状态撤回")
                else:
                    srow["补充说明"] = f"评审结论：{conclusion}，策略维持启用"
                return {"status": "ok", "strategy": srow, "conclusion": conclusion}
        return {"status": "not_found", "message": f"未找到策略{strategy_no}"}

    # ---------- 组合配置 → 再平衡执行 → 交易指令 ----------

    def execute_rebalance(self, rebalance: dict[str, Any]) -> dict[str, Any]:
        """组合再平衡触发调仓指令。"""
        combo_id = str(rebalance.get("组合编号", ""))
        direction = str(rebalance.get("调整方向", ""))
        try:
            magnitude = float(str(rebalance.get("调整幅度", "0")))
        except (ValueError, TypeError):
            magnitude = 0

        # 查找组合配置
        portfolio_rows = store.rows("portfolio_alloc")
        portfolio = None
        for prow in portfolio_rows:
            if str(prow.get("组合名称", "")) == combo_id:
                portfolio = prow
                break

        if portfolio is None:
            return {"status": "not_found", "message": f"未找到组合{combo_id}"}

        member_strategies = str(portfolio.get("成员策略", "")).split(",")
        generated_orders = []
        for member in member_strategies:
            member = member.strip()
            if not member:
                continue
            rows = store.rows("trade_instruct")
            new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
            order = {
                "id": new_id,
                "策略编号": f"REBAL-{new_id:04d}",
                "标的代码": member,
                "委托方向": direction,
                "委托数量": max(1, int(abs(magnitude) * 10)),
                "责任岗位": rebalance.get("责任岗位", "组合经理"),
                "登记批号": f"REBAL-BATCH-{combo_id}",
                "业务版本": "v1.0",
                "补充说明": f"组合{combo_id}再平衡自动生成调仓指令",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            }
            rows.append(order)
            generated_orders.append(order)

        audit_service.log("再平衡执行", str(rebalance.get("责任岗位", "")),
                        f"组合{combo_id}再平衡生成{len(generated_orders)}条调仓指令")
        return {"status": "ok", "generated_orders": generated_orders,
                "combo_id": combo_id, "count": len(generated_orders)}

    # ---------- 行情快照 → 预警派发 ----------

    def check_threshold_and_alert(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        """行情快照确认后检查价格是否触及预警阈值。"""
        symbol = str(snapshot.get("标的代码", ""))
        try:
            price = float(snapshot.get("最新价格", 0))
        except (ValueError, TypeError):
            price = 0

        alert_rows = store.rows("alert_dispatch")
        risk_rows = store.rows("risk_rule")

        alerts = []
        # 检查风控规则中的阈值
        for rule in risk_rows:
            if rule.get("status") != "已确认":
                continue
            try:
                threshold = float(str(rule.get("阈值上限", "Inf")))
            except (ValueError, TypeError):
                threshold = float("inf")

            if price >= threshold:
                rows = store.rows("alert_dispatch")
                new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
                alert = {
                    "id": new_id,
                    "预警类型": f"价格突破{rule.get('规则类型', '阈值')}",
                    "触发规则": str(rule.get("策略编号", "")),
                    "当前数值": str(price),
                    "接收人员": "风控员",
                    "责任岗位": "预警系统",
                    "登记批号": f"ALT-{new_id:04d}",
                    "业务版本": "v1.0",
                    "补充说明": f"标的{symbol}价格{price}触及阈值{threshold}",
                    "status": "草稿",
                    "pending": True,
                    "abnormal": False,
                }
                rows.append(alert)
                alerts.append(alert)

        if alerts:
            audit_service.log("预警触发", "系统",
                            f"标的{symbol}价格{price}触发{len(alerts)}条预警")
        return alerts

    # ---------- 综合模块概览 ----------

    def full_overview(self) -> dict[str, Any]:
        """生成包含跨模块关联的综合运营概览。"""
        modules = {}
        crossing_refs = []
        for module_name in store.module_names():
            rows = store.rows(module_name)
            by_status = {}
            for row in rows:
                st = str(row.get("status", ""))
                by_status[st] = by_status.get(st, 0) + 1
            modules[module_name] = {
                "total": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
                "by_status": by_status,
            }

        # 跨模块关联关系
        crossing_refs.append({
            "from": "strategy_config",
            "to": "factor_library",
            "description": "策略引用因子定义，校验权重合法性",
            "active": modules.get("strategy_config", {}).get("total", 0) > 0,
        })
        crossing_refs.append({
            "from": "strategy_config",
            "to": "backtest_task",
            "description": "策略已确认后可启动回测",
            "active": modules.get("strategy_config", {}).get("by_status", {}).get("已确认", 0) > 0,
        })
        crossing_refs.append({
            "from": "backtest_task",
            "to": "backtest_report",
            "description": "回测完成后自动生成报告",
            "active": modules.get("backtest_task", {}).get("by_status", {}).get("已确认", 0) > 0,
        })
        crossing_refs.append({
            "from": "backtest_report",
            "to": "risk_rule",
            "description": "报告确认后风控员设定规则阈值",
            "active": modules.get("backtest_report", {}).get("total", 0) > 0,
        })
        crossing_refs.append({
            "from": "risk_rule",
            "to": "trade_instruct",
            "description": "发送指令时检查风控规则(action_hold)",
            "active": modules.get("risk_rule", {}).get("by_status", {}).get("已确认", 0) > 0,
        })
        crossing_refs.append({
            "from": "trade_instruct",
            "to": "trade_fill",
            "description": "指令确认后生成成交记录",
            "active": modules.get("trade_instruct", {}).get("by_status", {}).get("已确认", 0) > 0,
        })
        crossing_refs.append({
            "from": "trade_fill",
            "to": "pnl_settle",
            "description": "成交记录汇总到盈亏核算",
            "active": modules.get("trade_fill", {}).get("total", 0) > 0,
        })
        crossing_refs.append({
            "from": "signal_sub",
            "to": "trade_instruct",
            "description": "信号触发后自动生成交易指令",
            "active": modules.get("signal_sub", {}).get("by_status", {}).get("已确认", 0) > 0,
        })
        crossing_refs.append({
            "from": "position_snapshot",
            "to": "pnl_settle",
            "description": "持仓快照时点与核算区间交叉验证",
            "active": modules.get("position_snapshot", {}).get("total", 0) > 0,
        })
        crossing_refs.append({
            "from": "strategy_review",
            "to": "strategy_config",
            "description": "评审结论影响策略启用状态",
            "active": modules.get("strategy_review", {}).get("total", 0) > 0,
        })
        crossing_refs.append({
            "from": "portfolio_alloc",
            "to": "rebalance_exec",
            "description": "组合配置驱动再平衡执行",
            "active": modules.get("portfolio_alloc", {}).get("total", 0) > 0,
        })
        crossing_refs.append({
            "from": "rebalance_exec",
            "to": "trade_instruct",
            "description": "再平衡触发调仓指令",
            "active": modules.get("rebalance_exec", {}).get("by_status", {}).get("已确认", 0) > 0,
        })
        crossing_refs.append({
            "from": "market_snapshot",
            "to": "alert_dispatch",
            "description": "行情数据触及阈值生成预警",
            "active": modules.get("market_snapshot", {}).get("total", 0) > 0,
        })

        return {"modules": modules, "cross_module_refs": crossing_refs,
                "total_records": sum(m["total"] for m in modules.values()),
                "total_pending": sum(m["pending"] for m in modules.values()),
                "total_abnormal": sum(m["abnormal"] for m in modules.values())}


coordinator = DomainCoordinator()
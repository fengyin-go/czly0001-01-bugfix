"""业务 API：跨模块操作端点，提供策略全链路的核心业务能力。

路径前缀 /api/business，区别于通用 CRUD 资源路由。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.domain_coordinator import coordinator

router = APIRouter(prefix="/api/business", tags=["业务操作"])


@router.get("/overview/full")
def full_overview() -> dict[str, Any]:
    """获取全模块综合概览，包含跨模块关联图。"""
    return coordinator.full_overview()


@router.post("/strategy/{strategy_id}/validate-factors")
def validate_strategy_factors(strategy_id: int) -> dict[str, Any]:
    """校验策略引用的因子定义是否合法。"""
    strategy = None
    for row_key in ["strategy_config"]:
        from app.store import store
        strategy = store.find("strategy_config", strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="策略不存在")
    return coordinator.validate_strategy_factors(strategy)


@router.post("/backtest/{task_id}/generate-report")
def generate_backtest_report(task_id: int) -> dict[str, Any]:
    """回测完成后自动生成回测报告。"""
    from app.store import store
    task = store.find("backtest_task", task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="回测任务不存在")
    if task.get("status") != "已确认":
        raise HTTPException(status_code=400, detail="回测任务未确认，无法生成报告")
    report = coordinator.generate_backtest_report(task)
    if report is None:
        return {"status": "exists", "message": "该回测任务已有对应报告"}
    return {"status": "ok", "report": report}


@router.get("/trade/{instruct_id}/risk-check")
def check_trade_risk(instruct_id: int) -> dict[str, Any]:
    """检查交易指令是否被风控规则阻止。"""
    from app.store import store
    trade = store.find("trade_instruct", instruct_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="交易指令不存在")
    return coordinator.check_risk_for_trade(trade)


@router.post("/trade/{instruct_id}/generate-fill")
def generate_trade_fill(instruct_id: int) -> dict[str, Any]:
    """交易指令确认后自动生成成交记录。"""
    from app.store import store
    instruct = store.find("trade_instruct", instruct_id)
    if instruct is None:
        raise HTTPException(status_code=404, detail="交易指令不存在")
    fill = coordinator.generate_trade_fill(instruct)
    if fill is None:
        return {"status": "exists", "message": "该指令已有确认的成交记录"}
    return {"status": "ok", "fill": fill}


@router.get("/pnl/summary/{strategy_no}")
def pnl_summary(strategy_no: str) -> dict[str, Any]:
    """获取策略的盈亏汇总。"""
    return coordinator.aggregate_pnl_by_strategy(strategy_no)


@router.post("/signal/{signal_id}/trigger-trade")
def trigger_trade_from_signal(signal_id: int) -> dict[str, Any]:
    """信号触发后自动生成交易指令。"""
    from app.store import store
    signal = store.find("signal_sub", signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="信号订阅不存在")
    if signal.get("status") != "已确认":
        raise HTTPException(status_code=400, detail="信号未确认，无法触发交易")
    instruct = coordinator.trigger_trade_from_signal(signal)
    if instruct is None:
        return {"status": "skipped", "message": "信号已处理或无效"}
    return {"status": "ok", "instruct": instruct}


@router.post("/review/{review_id}/apply-to-strategy")
def apply_review_to_strategy(review_id: int) -> dict[str, Any]:
    """策略评审结果应用到策略配置状态。"""
    from app.store import store
    review = store.find("strategy_review", review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="评审记录不存在")
    result = coordinator.apply_review_to_strategy(review)
    return result


@router.post("/rebalance/{rebalance_id}/execute")
def execute_rebalance(rebalance_id: int) -> dict[str, Any]:
    """执行再平衡并生成调仓指令。"""
    from app.store import store
    rebalance = store.find("rebalance_exec", rebalance_id)
    if rebalance is None:
        raise HTTPException(status_code=404, detail="再平衡记录不存在")
    if rebalance.get("status") != "已确认":
        raise HTTPException(status_code=400, detail="再平衡任务未确认")
    return coordinator.execute_rebalance(rebalance)


@router.post("/market/{snapshot_id}/check-alert")
def check_market_alert(snapshot_id: int) -> dict[str, Any]:
    """行情快照确认后检查并生成预警。"""
    from app.store import store
    snapshot = store.find("market_snapshot", snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="行情快照不存在")
    alerts = coordinator.check_threshold_and_alert(snapshot)
    return {"status": "ok", "alerts_count": len(alerts), "alerts": alerts}


@router.get("/audit/recent")
def recent_audits(limit: int = 20) -> dict[str, Any]:
    """获取最近的审计记录。"""
    from app.services.audit_trail import audit_service
    records = audit_service.recent_audits(limit=limit)
    return {"records": records, "total": len(records)}


@router.get("/audit/summary")
def audit_summary() -> dict[str, Any]:
    """审计记录按模块汇总。"""
    from app.services.audit_trail import audit_service
    return {"summary": audit_service.module_audit_summary()}


@router.get("/snapshot/{snapshot_id}/validate-settle")
def cross_validate_snapshot_settle(
    snapshot_id: int,
    interval_start: str = "",
    interval_end: str = "",
) -> dict[str, Any]:
    """持仓快照与盈亏核算区间交叉验证。"""
    from app.store import store
    snapshot = store.find("position_snapshot", snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="持仓快照不存在")
    settle_interval = f"{interval_start} ~ {interval_end}"
    return coordinator.cross_validate_snapshot_settle(snapshot, settle_interval)


@router.get("/report/{report_id}/risk-metrics")
def report_metrics_for_risk(report_id: int) -> dict[str, Any]:
    """获取回测报告的风控参考指标。"""
    return coordinator.report_metrics_for_risk(report_id)


@router.get("/strategy/{strategy_id}/can-launch-backtest")
def can_launch_backtest(strategy_id: int) -> dict[str, Any]:
    """检查策略是否可以启动回测。"""
    return coordinator.can_launch_backtest(strategy_id)
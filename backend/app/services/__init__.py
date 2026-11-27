"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.strategy_config import StrategyConfigService
from app.services.factor_library import FactorLibraryService
from app.services.backtest_task import BacktestTaskService
from app.services.backtest_report import BacktestReportService
from app.services.signal_sub import SignalSubService
from app.services.risk_rule import RiskRuleService
from app.services.position_snapshot import PositionSnapshotService
from app.services.exchange_binding import ExchangeBindingService
from app.services.trade_instruct import TradeInstructService
from app.services.trade_fill import TradeFillService
from app.services.pnl_settle import PnlSettleService
from app.services.capital_journal import CapitalJournalService
from app.services.strategy_review import StrategyReviewService
from app.services.portfolio_alloc import PortfolioAllocService
from app.services.rebalance_exec import RebalanceExecService
from app.services.market_snapshot import MarketSnapshotService
from app.services.alert_dispatch import AlertDispatchService
from app.services.operation_audit import OperationAuditService

SERVICES: dict[str, BaseModuleService] = {
    "strategy_config": StrategyConfigService(),
    "factor_library": FactorLibraryService(),
    "backtest_task": BacktestTaskService(),
    "backtest_report": BacktestReportService(),
    "signal_sub": SignalSubService(),
    "risk_rule": RiskRuleService(),
    "position_snapshot": PositionSnapshotService(),
    "exchange_binding": ExchangeBindingService(),
    "trade_instruct": TradeInstructService(),
    "trade_fill": TradeFillService(),
    "pnl_settle": PnlSettleService(),
    "capital_journal": CapitalJournalService(),
    "strategy_review": StrategyReviewService(),
    "portfolio_alloc": PortfolioAllocService(),
    "rebalance_exec": RebalanceExecService(),
    "market_snapshot": MarketSnapshotService(),
    "alert_dispatch": AlertDispatchService(),
    "operation_audit": OperationAuditService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)

"""回测引擎：处理回测任务的核心计算逻辑。

处理回测执行、参数校验、报告指标计算。
"""
from __future__ import annotations

from typing import Any

from app.store import store


class BacktestEngine:
    """回测执行引擎。"""

    def execute_backtest(self, task_id: int) -> dict[str, Any]:
        """执行回测任务并返回结果。"""
        task = store.find("backtest_task", task_id)
        if task is None:
            return {"status": "not_found"}
        if task.get("status") != "已确认":
            return {"status": "blocked", "reason": "任务未确认"}

        # 模拟回测执行
        result = self._run_simulation(task)
        return {"status": "ok", "task_id": task_id, "result": result}

    def _run_simulation(self, task: dict[str, Any]) -> dict[str, Any]:
        """运行回测模拟计算。"""
        import math
        import random
        random.seed(int(task.get("id", 1)))

        try:
            capital = float(str(task.get("初始本金", "100000")))
        except (ValueError, TypeError):
            capital = 100000

        trades = random.randint(50, 500)
        win_rate = random.uniform(0.4, 0.65)
        avg_win = random.uniform(0.01, 0.05)
        avg_loss = random.uniform(0.01, 0.04)

        # 模拟净值曲线
        equity = capital
        drawdowns = []
        peak = capital
        for _ in range(trades):
            if random.random() < win_rate:
                equity *= (1 + avg_win)
            else:
                equity *= (1 - avg_loss)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            drawdowns.append(dd)

        # 计算夏普比率
        returns = []
        curr = capital
        for _ in range(trades):
            if random.random() < win_rate:
                r = avg_win
            else:
                r = -avg_loss
            returns.append(r)
            curr *= (1 + r)

        mean_return = sum(returns) / len(returns) if returns else 0
        std_dev = math.sqrt(sum((r - mean_return) ** 2 for r in returns) / len(returns)) if returns else 1
        sharpe = mean_return / std_dev * math.sqrt(252) if std_dev > 0 else 0

        total_return = (equity - capital) / capital * 100
        max_dd = max(drawdowns) * 100 if drawdowns else 0

        return {
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "trade_count": trades,
            "win_rate": round(win_rate * 100, 1),
            "final_equity": round(equity, 2),
        }


class PnlEngine:
    """盈亏核算引擎。"""

    def calculate_realized_pnl(self, strategy_no: str) -> dict[str, Any]:
        """计算指定策略的已实现盈亏。"""
        fills = store.rows("trade_fill")
        confirmed = [f for f in fills
                    if f.get("status") == "已确认"
                    and str(f.get("指令编号", "")).startswith(strategy_no[:4])]

        total_gross = 0.0
        total_fee = 0.0
        buy_count = 0
        sell_count = 0
        for fill in confirmed:
            try:
                price = float(fill.get("成交价格", 0))
                quantity = int(fill.get("成交数量", 0))
                fee_rate = float(str(fill.get("手续费率", "0.001")))
            except (ValueError, TypeError):
                continue
            total_gross += price * quantity
            total_fee += price * quantity * fee_rate
            direction = str(fill.get("补充说明", ""))
            if "买入" in direction:
                buy_count += 1
            else:
                sell_count += 1 if sell_count >= 0 else 0

        return {
            "strategy_no": strategy_no,
            "gross_volume": round(total_gross, 2),
            "total_fee": round(total_fee, 4),
            "net_pnl": round(total_gross - total_fee, 2),
            "trade_count": len(confirmed),
            "buy_count": buy_count,
        }

    def calculate_unrealized_pnl(self, strategy_no: str) -> dict[str, Any]:
        """计算指定策略的未实现盈亏（基于持仓快照和最新行情）。"""
        positions = store.rows("position_snapshot")
        confirmed_pos = [p for p in positions if p.get("status") == "已确认"]

        total_unrealized = 0.0
        for pos in confirmed_pos:
            try:
                quantity = int(pos.get("持有数量", 0))
                cost_price = float(str(pos.get("成本均价", "0")))
            except (ValueError, TypeError):
                continue
            # 模拟行情价格
            import random
            symbol = str(pos.get("标的代码", ""))
            random.seed(hash(symbol) % 10000)
            current_price = cost_price * (1 + random.uniform(-0.15, 0.2))
            unrealized = (current_price - cost_price) * quantity
            total_unrealized += unrealized

        return {
            "strategy_no": strategy_no,
            "unrealized_pnl": round(total_unrealized, 2),
            "position_count": len(confirmed_pos),
        }


backtest_engine = BacktestEngine()
pnl_engine = PnlEngine()
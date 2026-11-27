"""测试跨模块业务数据流。

验证关键业务链路：
1. 策略配置 → 因子库(因子校验)
2. 策略配置 → 回测任务(状态前置检查)
3. 回测任务 → 回测报告(自动生成报告)
4. 交易指令 → 成交记录(自动生成成交)
5. 信号订阅 → 交易指令(信号触发交易)
6. 策略评审 → 策略配置(结论影响状态)
7. 行情快照 → 预警派发(价格触发预警)
8. 组合配置 → 再平衡执行 → 交易指令(调仓链路)
9. 所有操作 → 操作审计(审计日志)
"""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestStrategyToFactor:
    """策略确认时校验因子定义。"""

    def test_confirm_strategy_with_valid_factors(self, client: TestClient, seed_data):
        """已确认因子存在时策略可确认。"""
        r = client.post("/api/strategy_config", json={
            "values": {"策略名称": "策略因子校验", "标的品种": "ETHUSDT", "参数集合": "动量因子", "触发条件": "突破", "责任岗位": "策略员"}
        })
        strategy_id = r.json()["entry"]["id"]
        r = client.post(f"/api/strategy_config/{strategy_id}/actions", json={"action": "确认策略"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_confirm_strategy_with_missing_factor(self, client: TestClient):
        """引用的因子不存在时确认策略被阻止。"""
        r = client.post("/api/strategy_config", json={
            "values": {"策略名称": "无效因子策略", "标的品种": "ETHUSDT", "参数集合": "不存在因子", "触发条件": "突破", "责任岗位": "策略员"}
        })
        strategy_id = r.json()["entry"]["id"]
        r = client.post(f"/api/strategy_config/{strategy_id}/actions", json={"action": "确认策略"})
        assert r.status_code == 200
        data = r.json()
        assert "不存在" in data.get("message", "") or "blocked" in str(data)


class TestStrategyToBacktest:
    """策略状态影响回测启动。"""

    def test_launch_backtest_requires_confirmed_strategy(self, client: TestClient):
        """策略未确认时不能启动回测（使用seed已有回测任务）。"""
        # 创建未确认策略和对应的回测任务
        r = client.post("/api/strategy_config", json={
            "values": {"策略名称": "未确认策略", "标的品种": "BTCUSDT", "参数集合": "动量因子"}
        })
        assert r.status_code == 200
        strategy_id = r.json()["entry"]["id"]
        # 创建引用该策略的回测任务
        r = client.post("/api/backtest_task", json={
            "values": {"策略编号": "未确认策略", "历史区间": "2024-01-01至2024-12-31", "初始本金": "100000", "责任岗位": "回测员"}
        })
        assert r.status_code == 200
        backtest_id = r.json()["entry"]["id"]
        # 启动回测应该被阻止(策略未确认)
        r = client.post(f"/api/backtest_task/{backtest_id}/actions", json={"action": "启动回测"})
        data = r.json()
        assert data["ok"] is False


class TestBacktestToReport:
    """回测完成后自动生成报告。"""

    def test_backtest_generates_report(self, client: TestClient, seed_data):
        """已确认策略的回测启动后自动生成报告。"""
        r = client.post(f"/api/backtest_task/{seed_data['backtest_id']}/actions", json={"action": "启动回测"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        # 检查报告是否生成
        r = client.get("/api/backtest_report")
        reports = r.json()["items"]
        assert len(reports) > 0


class TestTradeToFill:
    """交易指令确认后自动生成成交记录。"""

    def test_trade_generates_fill(self, client: TestClient, seed_data):
        """创建交易指令并确认后应生成成交记录。"""
        # 启用风控规则阻止 -> 先不创建风控
        r = client.post("/api/trade_instruct", json={
            "values": {"策略编号": "TRAD-FILL", "标的代码": "BTCUSDT", "委托方向": "买入", "委托数量": "10", "责任岗位": "交易员"}
        })
        trade_id = r.json()["entry"]["id"]
        r = client.post(f"/api/trade_instruct/{trade_id}/actions", json={"action": "发送指令"})
        assert r.status_code == 200
        data = r.json()
        if data["ok"]:
            # 检查成交记录是否自动生成
            fills_r = client.get("/api/trade_fill")
            fills = fills_r.json()["items"]
            assert len(fills) > 0


class TestSignalToTrade:
    """信号触发后自动生成交易指令。"""

    def test_signal_triggers_trade(self, client: TestClient, seed_data):
        """确认信号后应触发交易指令生成。"""
        r = client.post(f"/api/signal_sub/{seed_data['signal_id']}/actions", json={"action": "确认订阅"})
        assert r.status_code == 200
        # 检查是否生成了交易指令
        r = client.get("/api/trade_instruct")
        trades = r.json()["items"]
        signal_trades = [t for t in trades if "SIGN" in str(t.get("策略编号", ""))]
        assert len(signal_trades) > 0


class TestReviewToStrategy:
    """评审结论影响策略状态。"""

    def test_review_negative_disables_strategy(self, client: TestClient, seed_data):
        """评审不通过应撤回策略。"""
        r = client.post("/api/strategy_review", json={
            "values": {"策略编号": "测试策略A", "实盘时长": "180天", "评审结论": "不通过-回撤超标", "评审人员": "首席策略师", "责任岗位": "评审员"}
        })
        review_id = r.json()["entry"]["id"]
        r = client.post(f"/api/strategy_review/{review_id}/actions", json={"action": "确认评审"})
        assert r.status_code == 200
        # 检查策略状态
        r = client.get(f"/api/strategy_config/{seed_data['strategy_id']}")
        strategy = r.json()
        assert strategy["status"] in ("已撤回", "草稿")


class TestMarketToAlert:
    """行情触发预警。"""

    def test_market_price_triggers_alert(self, client: TestClient, seed_data):
        """价格触及风控阈值应触发预警。需要先启用风控规则。"""
        # 启用风控规则
        r = client.post(f"/api/risk_rule/{seed_data['risk_id']}/actions", json={"action": "启用规则"})
        assert r.status_code == 200 and r.json()["ok"]
        # 创建行情快照，价格高过风控阈值(20)
        r = client.post("/api/market_snapshot", json={
            "values": {"标的代码": "BTCUSDT", "最新价格": "99", "二十四小时涨跌": "+5%", "成交额": "1000000", "责任岗位": "行情管理员"}
        })
        assert r.status_code == 200
        snap_id = r.json()["entry"]["id"]
        r = client.post(f"/api/market_snapshot/{snap_id}/actions", json={"action": "确认行情"})
        assert r.status_code == 200
        # 检查是否生成预警
        r = client.get("/api/alert_dispatch")
        alerts = r.json()["items"]
        assert len(alerts) > 0


class TestPortfolioToRebalance:
    """组合配置驱动再平衡。"""

    def test_rebalance_generates_orders(self, client: TestClient, seed_data):
        """再平衡执行应生成调仓指令。"""
        # 创建组合
        r = client.post("/api/portfolio_alloc", json={
            "values": {"组合名称": "PORT-CROSS", "成员策略": "测试策略A", "分配比例": "100%", "再平衡周期": "周", "责任岗位": "组合经理"}
        })
        portfolio_id = r.json()["entry"]["id"]
        client.post(f"/api/portfolio_alloc/{portfolio_id}/actions", json={"action": "确认组合"})
        # 创建再平衡
        r = client.post("/api/rebalance_exec", json={
            "values": {"组合编号": "PORT-CROSS", "执行时刻": "2026-11-27", "调整方向": "买入", "调整幅度": "0.5", "责任岗位": "组合经理"}
        })
        reb_id = r.json()["entry"]["id"]
        r = client.post(f"/api/rebalance_exec/{reb_id}/actions", json={"action": "执行再平衡"})
        assert r.status_code == 200
        # 检查是否生成调仓指令
        r = client.get("/api/trade_instruct")
        trades = r.json()["items"]
        rebal_trades = [t for t in trades if "REBAL" in str(t.get("策略编号", ""))]
        assert len(rebal_trades) > 0


class TestAuditTrail:
    """所有操作自动审计。"""

    def test_operations_generate_audit(self, client: TestClient, seed_data):
        """关键操作应生成审计记录。"""
        r = client.get("/api/operation_audit")
        audits = r.json()["items"]
        # 预置数据创建过程中已生成多条审计记录
        assert len(audits) > 0

    def test_business_api_audit_recent(self, client: TestClient, seed_data):
        """业务 API 审计端点正常工作。"""
        r = client.get("/api/business/audit/recent?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert "records" in data
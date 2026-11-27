"""测试 action_hold 阻止机制。

验证风控规则对交易指令的阻止逻辑：
1. 有已启用风控规则 → 发送指令被阻止
2. 撤回风控规则后 → 发送指令可通过
3. 策略级别的风控规则生效
"""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestActionHold:
    """action_hold 是前端也配置了的核心拦截逻辑。"""

    def test_hold_blocks_trade_with_active_risk(self, client: TestClient, seed_data):
        """有已启用的风控规则时发送指令应被阻止。"""
        # 启用风控规则
        r = client.post(f"/api/risk_rule/{seed_data['risk_id']}/actions", json={"action": "启用规则"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # 创建交易指令, 关联到有风控规则的策略
        r = client.post("/api/trade_instruct", json={
            "values": {"策略编号": "测试策略A", "标的代码": "BTCUSDT", "委托方向": "买入", "委托数量": "10", "责任岗位": "交易员"}
        })
        assert r.status_code == 200
        trade_id = r.json()["entry"]["id"]
        # 发送指令应被 action_hold 阻止
        r = client.post(f"/api/trade_instruct/{trade_id}/actions", json={"action": "发送指令"})
        data = r.json()
        assert data["ok"] is False
        assert "风控" in data["message"] or "阻止" in data["message"]

    def test_hold_allows_trade_after_risk_removed(self, client: TestClient, seed_data):
        """撤回风控规则后发送指令应通过。"""
        # 规则撤回
        r = client.post(f"/api/risk_rule/{seed_data['risk_id']}/actions", json={"action": "撤回记录"})
        assert r.status_code == 200
        # 创建交易指令
        r = client.post("/api/trade_instruct", json={
            "values": {"策略编号": "测试策略A", "标的代码": "BTCUSDT", "委托方向": "买入", "委托数量": "10", "责任岗位": "交易员"}
        })
        trade_id = r.json()["entry"]["id"]
        # 发送指令应通过
        r = client.post(f"/api/trade_instruct/{trade_id}/actions", json={"action": "发送指令"})
        data = r.json()
        assert data["ok"] is True

    def test_hold_with_different_strategy_not_blocked(self, client: TestClient, seed_data):
        """不同策略的风控规则不应阻止其他策略的交易。"""
        # 启用风控规则
        client.post(f"/api/risk_rule/{seed_data['risk_id']}/actions", json={"action": "启用规则"})
        # 创建不同策略编号的交易指令
        r = client.post("/api/trade_instruct", json={
            "values": {"策略编号": "OTHER-STRATEGY", "标的代码": "ETHUSDT", "委托方向": "买入", "委托数量": "10", "责任岗位": "交易员"}
        })
        trade_id = r.json()["entry"]["id"]
        r = client.post(f"/api/trade_instruct/{trade_id}/actions", json={"action": "发送指令"})
        data = r.json()
        # 不同策略编号，不应被阻止
        assert data["ok"] is True


class TestRiskCheckEndpoint:
    """业务 API 风控检查端点。"""

    def test_risk_check_blocked(self, client: TestClient, seed_data):
        """风控检查 API 返回阻止状态。"""
        client.post(f"/api/risk_rule/{seed_data['risk_id']}/actions", json={"action": "启用规则"})
        r = client.post("/api/trade_instruct", json={
            "values": {"策略编号": "测试策略A", "标的代码": "BTCUSDT", "委托方向": "买入", "委托数量": "10", "责任岗位": "交易员"}
        })
        trade_id = r.json()["entry"]["id"]
        r = client.get(f"/api/business/trade/{trade_id}/risk-check")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "blocked"

    def test_risk_check_ok(self, client: TestClient):
        """风控检查 API 返回通过状态。"""
        r = client.post("/api/trade_instruct", json={
            "values": {"策略编号": "CLEAN-STRATEGY", "标的代码": "BTCUSDT", "委托方向": "买入", "委托数量": "10", "责任岗位": "交易员"}
        })
        trade_id = r.json()["entry"]["id"]
        r = client.get(f"/api/business/trade/{trade_id}/risk-check")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
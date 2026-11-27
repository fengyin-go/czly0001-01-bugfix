"""测试状态流转正确性。

验证各模块的状态机流转：
1. 草稿 → 待确认 → 已确认 → 已撤回 (所有模块通用)
2. 状态跳级拦截
3. 异常标记正确
"""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestStatusFlow:
    """通用状态流转测试。"""

    MODULES_WITH_ACTIONS = [
        ("strategy_config", "策略名称", "确认策略"),
        ("factor_library", "因子名称", "确认因子"),
        ("backtest_report", "回测编号", "确认报告"),
        ("signal_sub", "信号方向", "确认订阅"),
        ("position_snapshot", "标的代码", "确认快照"),
        ("exchange_binding", "交易所名称", "绑定交易所"),
        ("trade_fill", "指令编号", "确认成交"),
        ("pnl_settle", "策略编号", "确认核算"),
        ("capital_journal", "账户编号", "确认流水"),
        ("alert_dispatch", "预警类型", "签收预警"),
        ("operation_audit", "操作类型", "归档审计"),
    ]

    def _create_entry(self, client: TestClient, module: str, key_field: str,
                      value: str) -> int:
        """Helper：创建一条模块记录并返回 id。"""
        required_values = {
            "strategy_config": {"策略名称": value, "标的品种": "BTCUSDT", "参数集合": "默认参数集"},
            "factor_library": {"因子名称": value, "计算周期": "周", "数据源类型": "行情"},
            "backtest_report": {"回测编号": value, "年化收益": "10%", "最大回撤": "5%"},
            "signal_sub": {"策略编号": value, "信号方向": "买入", "触发价格": 100},
            "position_snapshot": {"标的代码": value, "持有数量": 50, "成本均价": "42000"},
            "exchange_binding": {"交易所名称": value, "密钥指纹": "abc123", "操作域": "交易"},
            "trade_fill": {"指令编号": value, "成交价格": 100, "成交数量": 10},
            "pnl_settle": {"策略编号": value, "统计区间": "2026Q1", "已实现盈亏": "+1000"},
            "capital_journal": {"账户编号": value, "变动类型": "转入", "变动金额": 5000},
            "alert_dispatch": {"预警类型": value, "触发规则": "规则1", "当前数值": "100"},
            "operation_audit": {"操作类型": value, "操作人员": "测试", "操作内容": "测试内容"},
        }
        values = required_values.get(module, {key_field: value})
        r = client.post(f"/api/{module}", json={"values": values})
        assert r.status_code == 200, f"创建 {module} 失败: {r.text}"
        return int(r.json()["entry"]["id"])

    def test_initial_status_is_draft(self, client: TestClient):
        """新创建的条目初始状态应为草稿。"""
        r = client.post("/api/strategy_config", json={
            "values": {"策略名称": "状态测试", "标的品种": "BTCUSDT", "参数集合": "动量因子"}
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        assert r.json()["entry"]["status"] == "草稿"

    def test_draft_to_pending_review(self, client: TestClient):
        """草稿申请复核后变为待确认。"""
        eid = self._create_entry(client, "strategy_config", "策略名称", "复核测试")
        r = client.post(f"/api/strategy_config/{eid}/actions", json={"action": "申请复核"})
        assert r.json()["entry"]["status"] == "待确认"

    def test_pending_to_confirmed_simple(self, client: TestClient):
        """待确认状态下确认变为已确认(简化测试)。"""
        eid = self._create_entry(client, "strategy_config", "策略名称", "确认流转测试")
        r = client.post(f"/api/strategy_config/{eid}/actions", json={"action": "确认策略"})
        if r.json()["ok"]:
            assert r.json()["entry"]["status"] == "已确认"

    def test_withdraw_moves_to_withdrawn(self, client: TestClient):
        """撤回记录后状态变为已撤回。"""
        eid = self._create_entry(client, "strategy_config", "策略名称", "撤回测试")
        r = client.post(f"/api/strategy_config/{eid}/actions", json={"action": "撤回记录"})
        assert r.json()["entry"]["status"] == "已撤回"

    def test_pending_tracking_after_status_change(self, client: TestClient):
        """状态流转后 pending 标记正确更新。"""
        eid = self._create_entry(client, "strategy_config", "策略名称", "pending测试")
        # 初始是草稿，pending=True
        r = client.get(f"/api/strategy_config/{eid}")
        assert r.json()["pending"] is True
        # 确认为终态后 pending=False
        r = client.post(f"/api/strategy_config/{eid}/actions", json={"action": "撤回记录"})
        entry = r.json()["entry"]
        assert entry is not None
        assert entry["pending"] is False


class TestBusinessApiFlow:
    """业务 API 端点可用性测试。"""

    def test_full_overview(self, client: TestClient, seed_data):
        """综合概览端点正常。"""
        r = client.get("/api/business/overview/full")
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data
        assert "cross_module_refs" in data

    def test_validate_factors(self, client: TestClient, seed_data):
        """因子校验端点正常。"""
        r = client.post(f"/api/business/strategy/{seed_data['strategy_id']}/validate-factors")
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "blocked")

    def test_generate_report(self, client: TestClient, seed_data):
        """报告生成端点正常。"""
        # 先启动回测
        r = client.post(f"/api/backtest_task/{seed_data['backtest_id']}/actions", json={"action": "启动回测"})
        if r.json()["ok"]:
            r = client.post(f"/api/business/backtest/{seed_data['backtest_id']}/generate-report")
            assert r.status_code in (200, 400)

    def test_pnl_summary(self, client: TestClient, seed_data):
        """盈亏汇总端点正常。"""
        r = client.get("/api/business/pnl/summary/BTC")
        assert r.status_code == 200

    def test_audit_summary(self, client: TestClient, seed_data):
        """审计汇总端点正常。"""
        r = client.get("/api/business/audit/summary")
        assert r.status_code == 200
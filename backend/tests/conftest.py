"""测试配置文件：提供测试客户端和共享夹具。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_store():
    """每个测试前清空数据仓库保证测试隔离。"""
    from app import store
    store.store.clear()


@pytest.fixture
def client(reset_store):
    """FastAPI 测试客户端。"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def seed_data(client):
    """预置测试数据：策略、因子、风控规则、信号等。"""
    # 先创建因子
    r = client.post("/api/factor_library", json={
        "values": {"因子名称": "动量因子", "计算周期": "日", "数据源类型": "行情数据", "权重系数": "0.5", "责任岗位": "因子管理员"}
    })
    assert r.status_code == 200, f"Seed factor failed: {r.text}"
    factor_id = r.json()["entry"]["id"]
    client.post(f"/api/factor_library/{factor_id}/actions", json={"action": "确认因子"})
    
    # 创建策略
    r = client.post("/api/strategy_config", json={
        "values": {"策略名称": "测试策略A", "标的品种": "BTCUSDT", "参数集合": "动量因子", "触发条件": "价格突破", "责任岗位": "策略员"}
    })
    assert r.status_code == 200, f"Seed strategy failed: {r.text}"
    strategy_id = r.json()["entry"]["id"]
    client.post(f"/api/strategy_config/{strategy_id}/actions", json={"action": "确认策略"})
    
    # 创建回测任务
    r = client.post("/api/backtest_task", json={
        "values": {"策略编号": "测试策略A", "历史区间": "2024-01-01至2024-12-31", "初始本金": "100000", "责任岗位": "回测员"}
    })
    backtest_id = r.json()["entry"]["id"]
    
    # 创建风控规则
    r = client.post("/api/risk_rule", json={
        "values": {"策略编号": "测试策略A", "规则类型": "最大回撤限制", "阈值上限": "20", "适用策略": "测试策略A", "生效范围": "全局", "责任岗位": "风控员"}
    })
    risk_id = r.json()["entry"]["id"]
    
    # 创建信号
    r = client.post("/api/signal_sub", json={
        "values": {"策略编号": "测试策略A", "信号方向": "买入", "触发价格": "100", "有效期限": "2026-12-31", "责任岗位": "信号员"}
    })
    signal_id = r.json()["entry"]["id"]
    
    return {
        "strategy_id": strategy_id,
        "factor_id": factor_id,
        "backtest_id": backtest_id,
        "risk_id": risk_id,
        "signal_id": signal_id,
    }
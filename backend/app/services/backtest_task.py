"""回测任务领域服务：回测单的登记、启动、完成后自动生成报告。

跨模块数据流：
- 启动回测 → 前置检查策略状态为已确认(来自 strategy_config)
- 回测完成后 → 自动生成回测报告(写入 backtest_report)
- 回测参数 → 影响风控规则阈值设定
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class BacktestTaskService(BaseModuleService):
    MODULE = "backtest_task"
    ENTITY = "回测单"
    OPERATION_TERM = "启动回测"
    ACTION_HOLD = None
    LIST_FIELDS = ["策略编号", "历史区间", "初始本金", "执行状态", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "历史区间", "初始本金"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"启动回测": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        """启动回测前检查策略状态是否为已确认。"""
        if action == "启动回测":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            # 跨模块检查：关联策略必须为已确认状态
            strategy_no = str(entry.get("策略编号", ""))
            from app.services.domain_coordinator import coordinator
            # 尝试根据策略编号定位策略
            strategy_rows = store.rows("strategy_config")
            matched = None
            for srow in strategy_rows:
                if str(srow.get("策略名称", "")) == strategy_no:
                    matched = srow
                    break
            if matched and matched.get("status") != "已确认":
                return None, f"关联策略「{strategy_no}」当前状态为「{matched.get('status')}」，需先确认为「已确认」后才能启动回测"
            # 执行基础动作
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "回测员")),
                                f"回测任务{entry_id}已启动，关联策略{strategy_no}",
                                module_source=self.MODULE, entry_id=entry_id)
                # 回测完成后自动生成报告
                coordinator.generate_backtest_report(result[0])
            return result
        return super().run_action(entry_id, action)

    def get_backtests_for_strategy(self, strategy_no: str) -> list[dict[str, Any]]:
        """获取指定策略的所有回测任务。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if str(row.get("策略编号", "")) == strategy_no]
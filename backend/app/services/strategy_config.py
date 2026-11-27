"""策略配置领域服务：策略单的登记、确认、因子校验、回测启动前置检查。

跨模块数据流：
- 确认策略 → 校验引用的因子定义是否存在且权重合法
- 已确认策略 → 允许启动回测任务
- 策略评审结论 → 影响策略启用/撤回状态
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class StrategyConfigService(BaseModuleService):
    MODULE = "strategy_config"
    ENTITY = "策略单"
    OPERATION_TERM = "确认策略"
    ACTION_HOLD = None
    LIST_FIELDS = ["策略名称", "标的品种", "参数集合", "触发条件", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略名称", "标的品种", "参数集合"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认策略": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        """重写动作执行：确认策略时增加因子校验。"""
        if action == "确认策略":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            # 跨模块校验：确认策略前检查因子库
            from app.services.domain_coordinator import coordinator
            factor_check = coordinator.validate_strategy_factors(entry)
            if factor_check["status"] == "blocked":
                return None, factor_check["message"]
            # 执行基础动作
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "策略员")),
                                f"策略{entry.get('策略名称')}已确认，引用{factor_check.get('factors', [])}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_validated_strategies(self) -> list[dict[str, Any]]:
        """获取所有已确认且因子校验通过的策略。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") == "已确认" and not row.get("abnormal")]

    def strategy_with_factors(self, entry_id: int) -> dict[str, Any]:
        """获取策略及其引用的因子详情。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"status": "not_found"}
        from app.services.domain_coordinator import coordinator
        factor_check = coordinator.validate_strategy_factors(entry)
        return {"strategy": entry, "factor_validation": factor_check}
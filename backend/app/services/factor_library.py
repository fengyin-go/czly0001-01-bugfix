"""因子库领域服务：因子定义的登记、确认、权重校验、策略引用查询。

跨模块数据流：
- 因子定义 → 被策略配置引用，校验权重合法性
- 因子权重变化 → 影响已确认策略的风险评估
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


class FactorLibraryService(BaseModuleService):
    MODULE = "factor_library"
    ENTITY = "因子定义"
    OPERATION_TERM = "确认因子"
    ACTION_HOLD = None
    LIST_FIELDS = ["因子名称", "计算周期", "数据源类型", "权重系数", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["因子名称", "计算周期", "数据源类型"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认因子": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        """确认因子时校验权重系数合法性。"""
        if action == "确认因子":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            try:
                weight = float(str(entry.get("权重系数", "0")))
                if not 0 < weight <= 1:
                    return None, f"权重系数{weight}不合法，需在0-1之间"
            except (ValueError, TypeError):
                return None, "权重系数必须为有效数值"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "因子管理员")),
                                f"因子{entry.get('因子名称')}已确认，权重{weight}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_confirmed_factors(self) -> list[dict[str, Any]]:
        """获取所有已确认的因子定义。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") == "已确认"]

    def find_strategies_using_factor(self, factor_name: str) -> list[dict[str, Any]]:
        """查找引用指定因子的所有策略。"""
        strategy_rows = store.rows("strategy_config")
        result = []
        for srow in strategy_rows:
            params = str(srow.get("参数集合", ""))
            if factor_name in params.split(","):
                result.append(srow)
        return result
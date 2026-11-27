"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RebalanceExecService(BaseModuleService):
    MODULE = "rebalance_exec"
    ENTITY = "再平衡单"
    OPERATION_TERM = "执行再平衡"
    ACTION_HOLD = None
    LIST_FIELDS = ["组合编号", "执行时刻", "调整方向", "调整幅度", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["组合编号", "执行时刻", "调整方向"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"执行再平衡": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

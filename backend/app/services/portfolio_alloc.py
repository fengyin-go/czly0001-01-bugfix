"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PortfolioAllocService(BaseModuleService):
    MODULE = "portfolio_alloc"
    ENTITY = "组合单"
    OPERATION_TERM = "确认组合"
    ACTION_HOLD = None
    LIST_FIELDS = ["组合名称", "成员策略", "分配比例", "再平衡周期", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["组合名称", "成员策略", "分配比例"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"确认组合": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

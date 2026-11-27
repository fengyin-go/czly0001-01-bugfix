"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AlertDispatchService(BaseModuleService):
    MODULE = "alert_dispatch"
    ENTITY = "预警单"
    OPERATION_TERM = "签收预警"
    ACTION_HOLD = None
    LIST_FIELDS = ["预警类型", "触发规则", "当前数值", "接收人员", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["预警类型", "触发规则", "当前数值"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"签收预警": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

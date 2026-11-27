"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class OperationAuditService(BaseModuleService):
    MODULE = "operation_audit"
    ENTITY = "审计单"
    OPERATION_TERM = "归档审计"
    ACTION_HOLD = None
    LIST_FIELDS = ["操作类型", "操作人员", "操作内容", "操作时刻", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["操作类型", "操作人员", "操作内容"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"归档审计": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

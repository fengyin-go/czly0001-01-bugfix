"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ExchangeBindingService(BaseModuleService):
    MODULE = "exchange_binding"
    ENTITY = "绑定单"
    OPERATION_TERM = "绑定交易所"
    ACTION_HOLD = None
    LIST_FIELDS = ["交易所名称", "密钥指纹", "操作域", "绑定时刻", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["交易所名称", "密钥指纹", "操作域"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"绑定交易所": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

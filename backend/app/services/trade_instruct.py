"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class TradeInstructService(BaseModuleService):
    MODULE = "trade_instruct"
    ENTITY = "指令单"
    OPERATION_TERM = "发送指令"
    ACTION_HOLD = {'action': '发送指令', 'source': 'risk_rule', 'match_field': '策略编号', 'source_status': '已确认', 'message': '对应策略仍有已启用的风控规则在生效，当前不能发送指令'}
    LIST_FIELDS = ["策略编号", "标的代码", "委托方向", "委托数量", "责任岗位", "登记批号", "业务版本", "补充说明"]
    REQUIRED_FIELDS = ["策略编号", "标的代码", "委托方向"]
    STATUS_ORDER = ["草稿", "待确认", "已确认", "已撤回"]
    ACTION_RULES = {"发送指令": "已确认", "申请复核": "待确认", "撤回记录": "已撤回"}
    NEGATIVE_ACTIONS = []

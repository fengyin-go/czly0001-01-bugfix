"""数据模型：业务实体定义和校验规则。

定义各模块的实体校验、字段约束和业务规则。
"""
from __future__ import annotations

from typing import Any


class StrategyValidator:
    """策略配置校验器。"""

    @staticmethod
    def validate_strategy_name(name: str) -> tuple[bool, str]:
        if not name or not str(name).strip():
            return False, "策略名称不能为空"
        if len(str(name)) > 64:
            return False, "策略名称超过64字符"
        return True, ""

    @staticmethod
    def validate_target_symbol(symbol: str) -> tuple[bool, str]:
        valid_symbols = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"}
        if str(symbol) not in valid_symbols:
            return False, f"标的品种{symbol}不在支持列表中"
        return True, ""


class FactorValidator:
    """因子定义校验器。"""

    @staticmethod
    def validate_weight(weight: Any) -> tuple[bool, str]:
        try:
            w = float(str(weight))
            if not 0 < w <= 1:
                return False, "权重系数需在0-1之间"
            return True, ""
        except (ValueError, TypeError):
            return False, "权重系数必须为有效数值"

    @staticmethod
    def validate_period(period: str) -> tuple[bool, str]:
        valid_periods = {"日", "周", "月", "季", "年"}
        if str(period) not in valid_periods:
            return False, f"计算周期{period}不支持，支持：{'、'.join(valid_periods)}"
        return True, ""


class RiskRuleValidator:
    """风控规则校验器。"""

    RULE_TYPES = {"最大回撤限制", "单笔亏损限制", "日亏损限制", "持仓集中度", "杠杆倍率限制"}

    @staticmethod
    def validate_rule_type(rule_type: str) -> tuple[bool, str]:
        if str(rule_type) not in RiskRuleValidator.RULE_TYPES:
            return False, f"规则类型{rule_type}不支持"
        return True, ""

    @staticmethod
    def validate_threshold(threshold: Any) -> tuple[bool, str]:
        try:
            t = float(str(threshold))
            if t <= 0:
                return False, "阈值必须为正数"
            return True, ""
        except (ValueError, TypeError):
            return False, "阈值必须为有效数值"


class TradeOrderValidator:
    """交易指令校验器。"""

    DIRECTIONS = {"买入", "卖出"}

    @staticmethod
    def validate_direction(direction: str) -> tuple[bool, str]:
        if str(direction) not in TradeOrderValidator.DIRECTIONS:
            return False, f"委托方向{direction}不支持"
        return True, ""

    @staticmethod
    def validate_quantity(quantity: Any) -> tuple[bool, str]:
        try:
            q = int(str(quantity))
            if q <= 0:
                return False, "委托数量必须为正整数"
            if q > 1000000:
                return False, "委托数量超过单笔上限"
            return True, ""
        except (ValueError, TypeError):
            return False, "委托数量必须为有效整数"
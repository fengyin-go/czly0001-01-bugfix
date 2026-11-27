"""交易所绑定领域服务：绑定单的登记、确认，交易权限校验。

跨模块数据流：
- 交易所绑定 → 交易指令(绑定确认后授权在该交易所执行交易)
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store
from app.services.audit_trail import audit_service


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

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        if action == "绑定交易所":
            entry = store.find(self.MODULE, entry_id)
            if entry is None:
                return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
            result = super().run_action(entry_id, action)
            if result[0] is not None:
                audit_service.log(action, str(entry.get("责任岗位", "管理员")),
                                f"交易所{entry.get('交易所名称')}已绑定，操作域{entry.get('操作域')}",
                                module_source=self.MODULE, entry_id=entry_id)
            return result
        return super().run_action(entry_id, action)

    def get_active_bindings(self) -> list[dict[str, Any]]:
        """获取所有已确认的交易所绑定。"""
        rows = store.rows(self.MODULE)
        return [row for row in rows if row.get("status") == "已确认"]

    def is_exchange_bound(self, exchange_name: str) -> bool:
        """检查交易所是否已绑定且确认。"""
        for row in store.rows(self.MODULE):
            if str(row.get("交易所名称", "")) == exchange_name and row.get("status") == "已确认":
                return True
        return False
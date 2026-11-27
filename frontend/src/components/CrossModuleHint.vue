<template>
  <aside class="cross-hint-panel" :data-testid="`hint-${moduleKey}`">
    <h4 class="hint-title">跨模块依赖</h4>
    <ul class="hint-list">
      <li v-for="ref in relevantRefs" :key="`${ref.from}-${ref.to}`" class="hint-item" :class="{ active: ref.active }">
        <span class="hint-arrow">{{ ref.from_cn }} → {{ ref.to_cn }}</span>
        <span class="hint-desc">{{ ref.description }}</span>
        <span v-if="ref.active" class="hint-badge active">活跃</span>
        <span v-else class="hint-badge inactive">未激活</span>
      </li>
      <li v-if="!relevantRefs.length" class="hint-empty">
        暂无跨模块依赖关系
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const MODULE_CN_MAP: Record<string, string> = {
  strategy_config: '策略配置',
  factor_library: '因子库',
  backtest_task: '回测任务',
  backtest_report: '回测报告',
  signal_sub: '信号订阅',
  risk_rule: '风控规则',
  position_snapshot: '持仓快照',
  exchange_binding: '交易所绑定',
  trade_instruct: '交易指令',
  trade_fill: '成交记录',
  pnl_settle: '盈亏核算',
  capital_journal: '资金流水',
  strategy_review: '策略评审',
  portfolio_alloc: '组合配置',
  rebalance_exec: '再平衡执行',
  market_snapshot: '行情快照',
  alert_dispatch: '预警派发',
  operation_audit: '操作审计',
}

const props = defineProps<{
  moduleKey: string
  crossRefs: { from: string; to: string; description: string; active: boolean }[]
}>()

const relevantRefs = computed(() => {
  return props.crossRefs
    .filter((ref) => ref.from === props.moduleKey || ref.to === props.moduleKey)
    .map((ref) => ({
      ...ref,
      from_cn: MODULE_CN_MAP[ref.from] || ref.from,
      to_cn: MODULE_CN_MAP[ref.to] || ref.to,
    }))
})
</script>
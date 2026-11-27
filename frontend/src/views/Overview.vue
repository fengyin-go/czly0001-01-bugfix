<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="refresh">刷新概览</button>
      </div>
    </header>

    <!-- 总量卡片 -->
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <!-- 业务模块明细表 -->
    <h3 class="section-title">模块明细</h3>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>记录数</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name" :class="{ hasAbnormal: row.abnormal > 0, hasPending: row.pending > 0 }">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td :class="{ warn: row.pending > 0 }">{{ row.pending }}</td>
          <td :class="{ error: row.abnormal > 0 }">{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 跨模块关联图 -->
    <h3 class="section-title">跨模块数据流</h3>
    <div v-if="crossRefs.length" class="cross-refs-panel">
      <div
        v-for="ref in crossRefs"
        :key="`${ref.from}-${ref.to}`"
        class="cross-ref-item"
        :class="{ active: ref.active }"
      >
        <span class="ref-arrow">{{ getModuleName(ref.from) }} → {{ getModuleName(ref.to) }}</span>
        <span class="ref-desc">{{ ref.description }}</span>
        <span :class="ref.active ? 'badge-ok' : 'badge-off'">{{ ref.active ? '活跃' : '待激活' }}</span>
      </div>
    </div>

    <!-- 实时审计时间线 -->
    <h3 class="section-title">最近操作</h3>
    <div v-if="auditRecords.length" class="audit-timeline">
      <div v-for="audit in auditRecords.slice(0, 10)" :key="audit.id" class="audit-item">
        <span class="audit-time">{{ audit['操作时刻'] }}</span>
        <span class="audit-type">{{ audit['操作类型'] }}</span>
        <span class="audit-content">{{ audit['操作内容'] }}</span>
      </div>
    </div>
    <p v-else class="empty-hint">暂无操作记录</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchJson } from '@/api/client'
import type { OverviewResult } from '@/data/types'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

const MODULE_NAMES: Record<string, string> = {
  strategy_config: '策略配置', factor_library: '因子库', backtest_task: '回测任务',
  backtest_report: '回测报告', signal_sub: '信号订阅', risk_rule: '风控规则',
  position_snapshot: '持仓快照', exchange_binding: '交易所绑定', trade_instruct: '交易指令',
  trade_fill: '成交记录', pnl_settle: '盈亏核算', capital_journal: '资金流水',
  strategy_review: '策略评审', portfolio_alloc: '组合配置', rebalance_exec: '再平衡执行',
  market_snapshot: '行情快照', alert_dispatch: '预警派发', operation_audit: '操作审计',
}

const cards = ref<{ label: string; value: number }[]>([])
const moduleRows = ref<{ name: string; created: number; pending: number; abnormal: number }[]>([])
const crossRefs = ref<{ from: string; to: string; description: string; active: boolean }[]>([])
const auditRecords = ref<Record<string, string | number>[]>([])

function getModuleName(key: string): string {
  return MODULE_NAMES[key] || key
}

async function refresh() {
  try {
    // 基础概览
    const payload = await fetchJson<OverviewResult>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{ label: '业务模块', value: 0 }, { label: '今日新增', value: 0 }]
    moduleRows.value = [
      { name: '策略配置', created: 0, pending: 0, abnormal: 0 },
      { name: '因子库', created: 0, pending: 0, abnormal: 0 },
    ]
  }

  try {
    // 跨模块概览
    const overviewRes = await fetchJson<{
      cross_module_refs: { from: string; to: string; description: string; active: boolean }[]
    }>('/api/business/overview/full')
    crossRefs.value = overviewRes.cross_module_refs
  } catch {
    crossRefs.value = []
  }

  try {
    // 审计时间线
    const auditRes = await fetchJson<{ records: Record<string, string | number>[] }>('/api/business/audit/recent?limit=10')
    auditRecords.value = auditRes.records
  } catch {
    auditRecords.value = []
  }
}

onMounted(refresh)
</script>

<style scoped>
.section-title {
  margin: 24px 0 12px;
  font-size: 16px;
  color: #303133;
  border-bottom: 2px solid #409eff;
  padding-bottom: 6px;
}

.cross-refs-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.cross-ref-item {
  padding: 8px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fafafa;
}

.cross-ref-item.active {
  border-color: #67c23a;
  background: #f0f9eb;
}

.ref-arrow { font-weight: 600; color: #409eff; }
.ref-desc { color: #606266; flex: 1; }

.badge-ok { color: #67c23a; font-size: 12px; font-weight: 600; }
.badge-off { color: #c0c4cc; font-size: 12px; }

.audit-timeline {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px;
}

.audit-item {
  display: flex;
  gap: 14px;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
}

.audit-item:last-child { border-bottom: none; }
.audit-time { color: #909399; white-space: nowrap; min-width: 140px; }
.audit-type { color: #409eff; font-weight: 600; white-space: nowrap; min-width: 80px; }
.audit-content { color: #303133; }

.empty-hint { color: #c0c4cc; font-size: 13px; }

tr.hasAbnormal td { background: #fef0f0; }
tr.hasPending td { background: #fff7e6; }
td.warn { color: #e6a23c; font-weight: 600; }
td.error { color: #f56c6c; font-weight: 600; }
</style>
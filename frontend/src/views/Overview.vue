<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "策略配置", "created": 0, "pending": 0, "abnormal": 0}, {"name": "因子库", "created": 0, "pending": 0, "abnormal": 0}, {"name": "回测任务", "created": 0, "pending": 0, "abnormal": 0}, {"name": "回测报告", "created": 0, "pending": 0, "abnormal": 0}, {"name": "信号订阅", "created": 0, "pending": 0, "abnormal": 0}, {"name": "风控规则", "created": 0, "pending": 0, "abnormal": 0}, {"name": "持仓快照", "created": 0, "pending": 0, "abnormal": 0}, {"name": "交易所绑定", "created": 0, "pending": 0, "abnormal": 0}, {"name": "交易指令", "created": 0, "pending": 0, "abnormal": 0}, {"name": "成交记录", "created": 0, "pending": 0, "abnormal": 0}, {"name": "盈亏核算", "created": 0, "pending": 0, "abnormal": 0}, {"name": "资金流水", "created": 0, "pending": 0, "abnormal": 0}, {"name": "策略评审", "created": 0, "pending": 0, "abnormal": 0}, {"name": "组合配置", "created": 0, "pending": 0, "abnormal": 0}, {"name": "再平衡执行", "created": 0, "pending": 0, "abnormal": 0}, {"name": "行情快照", "created": 0, "pending": 0, "abnormal": 0}, {"name": "预警派发", "created": 0, "pending": 0, "abnormal": 0}, {"name": "操作审计", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>

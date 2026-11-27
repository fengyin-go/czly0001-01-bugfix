<template>
  <section class="page" :data-module="meta.key">
    <header class="page-head">
      <div>
        <h2>{{ meta.name }}</h2>
        <p class="page-desc">{{ meta.desc }}</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" data-testid="open-create" type="button" @click="openCreate">
          登记{{ meta.entity }}
        </button>
        <button class="btn" data-testid="export" type="button" @click="exportRows">
          导出{{ meta.name }}清单
        </button>
        <button class="btn ghost" data-testid="toggle-hints" type="button" @click="showHints = !showHints">
          {{ showHints ? '收起跨模块' : '跨模块依赖' }}
        </button>
      </div>
    </header>

    <!-- 跨模块依赖提示面板 -->
    <CrossModuleHint
      v-if="showHints && crossRefs.length"
      :module-key="meta.key"
      :cross-refs="crossRefs"
    />

    <!-- 状态流转概览 -->
    <div class="status-flow" data-testid="status-flow">
      <span class="flow-label">状态流转：</span>
      <span
        v-for="(status, idx) in meta.statuses"
        :key="status"
        class="flow-node"
        :class="{
          current: rows.length && rows[0]?.status === status,
          terminal: idx === meta.statuses.length - 1,
        }"
      >
        {{ status }}
        <span v-if="idx < meta.statuses.length - 1" class="flow-arrow">→</span>
      </span>
    </div>

    <!-- 动作拦截提示 -->
    <div v-if="meta.hold" class="hold-hint" data-testid="hold-hint">
      提醒：{{ meta.hold.message }}
      <span class="hold-source">（来源模块：{{ meta.hold.source }}）</span>
    </div>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <p class="status-legend">
      <span v-for="item in statusSummary" :key="item.status" class="legend-item" :class="{ active: item.count > 0, zero: item.count === 0 }">
        {{ item.status }}：{{ item.count }}
      </span>
    </p>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :data-testid="`filter-${field}`" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" data-testid="query" type="submit">查询</button>
      <button class="btn ghost" data-testid="reset" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in meta.fields" :key="column">{{ column }}</th>
          <th>当前状态</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :data-testid="`row-${row.id}`" :data-status="String(row.status)" :class="{ abnormal: row.abnormal }">
          <td v-for="column in meta.fields" :key="column">{{ row[column] ?? '—' }}</td>
          <td>
            <span class="status-badge" :class="statusClass(row.status)">{{ row.status }}</span>
          </td>
          <td class="row-actions">
            <button
              v-for="action in meta.actions"
              :key="action"
              class="link"
              :class="{ blocked: isActionBlocked(action, row) }"
              type="button"
              :data-testid="`action-${row.id}-${action}`"
              :title="getActionHint(action, row)"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="meta.fields.length + 2" class="empty-state">
            暂无{{ meta.name }}数据，可先登记{{ meta.entity }}
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 分页信息 -->
    <footer class="page-foot">
      <span>共 {{ total }} 条{{ meta.name }}记录</span>
      <span>第 {{ page }} / {{ Math.ceil(total / pageSize) || 1 }} 页</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <!-- 登记弹窗 -->
    <div v-if="showCreate" class="modal-backdrop" data-testid="create-modal">
      <form class="modal" @submit.prevent="submitCreate">
        <h3>登记{{ meta.entity }}</h3>
        <label v-for="field in meta.fields" :key="field" class="create-field">
          <span>{{ field }}</span>
          <input v-model="createValues[field]" :data-testid="`create-${field}`" :required="isRequired(field)" />
        </label>
        <div class="page-actions">
          <button class="btn" type="button" @click="showCreate = false">取消</button>
          <button class="btn primary" data-testid="submit-create" type="submit" :disabled="creating">
            {{ creating ? '提交中…' : '确认登记' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  createEntry,
  downloadEntries,
  listEntries,
  moduleMeta,
  runAction as applyAction,
} from '@/api/backend-service'
import type { EntryRow } from '@/data/types'
import CrossModuleHint from '@/components/CrossModuleHint.vue'

const props = defineProps<{ moduleKey: string }>()
const meta = moduleMeta(props.moduleKey)
const rows = ref<EntryRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = meta.fields.slice(0, 3)
const showCreate = ref(false)
const creating = ref(false)
const showHints = ref(false)
const createValues = ref<Record<string, string>>({})

// 跨模块引用关系
const crossRefs = ref<{ from: string; to: string; description: string; active: boolean }[]>([])

const stats = computed(() => [
  { label: meta.metrics[0], value: total.value },
  { label: meta.metrics[1], value: rows.value.filter((row) => row.status === meta.statuses[1]).length },
  {
    label: meta.metrics[2],
    value: rows.value.filter((row) => row.status === meta.statuses[meta.statuses.length - 1]).length,
  },
])

const statusSummary = computed(() =>
  meta.statuses.map((status) => ({
    status,
    count: rows.value.filter((row) => String(row.status) === status).length,
  })),
)

function statusClass(status: string): string {
  if (status === '已确认') return 'confirmed'
  if (status === '已撤回') return 'withdrawn'
  if (status === '待确认') return 'pending-review'
  return 'draft'
}

function isActionBlocked(action: string, row: EntryRow): boolean {
  if (!meta.hold) return false
  return action === meta.hold.action
}

function getActionHint(action: string, row: EntryRow): string {
  if (isActionBlocked(action, row)) {
    return meta.hold?.message || '有跨模块依赖阻止该操作'
  }
  const target = meta.actionTargets[action]
  return target ? `${row.status} → ${target}` : ''
}

function isRequired(field: string): boolean {
  const requiredFields = ['策略编号', '策略名称', '标的品种', '因子名称', '回测编号', '规则类型', '预警类型', '操作类型', '标的代码', '组合名称']
  return requiredFields.some((f) => field.includes(f) || meta.fields.indexOf(field) < 3)
}

function resetFilters() {
  filters.value = {}
  page.value = 1
  void reload()
}

async function exportRows() {
  errorMessage.value = ''
  try {
    await downloadEntries(meta.key, filters.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '导出失败'
  }
}

function openCreate() {
  createValues.value = Object.fromEntries(meta.fields.map((field) => [field, '']))
  errorMessage.value = ''
  showCreate.value = true
}

async function submitCreate() {
  creating.value = true
  errorMessage.value = ''
  try {
    const result = await createEntry(meta.key, createValues.value)
    if (!result.ok) throw new Error(result.message)
    showCreate.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登记失败'
  } finally {
    creating.value = false
  }
}

async function runAction(action: string, row: EntryRow) {
  errorMessage.value = ''
  try {
    const result = await applyAction(meta.key, Number(row.id), action)
    if (!result.ok) throw new Error(result.message)
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  try {
    const payload = await listEntries(meta.key, filters.value)
    rows.value = payload.items
    total.value = payload.total
    page.value = payload.page
    pageSize.value = payload.size
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '业务列表读取失败'
  }
}

async function loadCrossRefs() {
  try {
    const { loadFullOverview } = await import('@/api/dashboard')
    const overview = await loadFullOverview()
    crossRefs.value = overview.cross_module_refs
  } catch {
    // 跨模块数据加载失败不影响主流程
  }
}

onMounted(() => {
  void reload()
  void loadCrossRefs()
})
</script>

<style scoped>
.status-flow {
  margin: 8px 0 16px;
  padding: 10px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.flow-label { color: #606266; margin-right: 8px; }
.flow-node { color: #909399; }
.flow-node.current { color: #409eff; font-weight: 600; }
.flow-node.terminal { color: #e6a23c; }
.flow-arrow { margin: 0 6px; color: #c0c4cc; }

.hold-hint {
  margin: 0 0 12px;
  padding: 8px 14px;
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
  color: #f56c6c;
  font-size: 13px;
  border-radius: 4px;
}
.hold-source {
  color: #909399;
  font-size: 12px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}
.status-badge.confirmed { background: #e1f3d8; color: #67c23a; }
.status-badge.pending-review { background: #faecd8; color: #e6a23c; }
.status-badge.withdrawn { background: #fef0f0; color: #f56c6c; }
.status-badge.draft { background: #ecf5ff; color: #909399; }

.legend-item.active { color: #303133; }
.legend-item.zero { color: #c0c4cc; }

.row-actions .link.blocked {
  color: #f56c6c;
  text-decoration: line-through;
  cursor: not-allowed;
}

tr.abnormal td {
  background: #fef0f0 !important;
}
</style>
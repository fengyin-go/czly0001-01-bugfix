/** 业务 API 客户端：跨模块操作和大盘概览。 */
import { request } from './client'

export type FullOverview = {
  modules: Record<string, {
    total: number
    pending: number
    abnormal: number
    by_status: Record<string, number>
  }>
  cross_module_refs: {
    from: string
    to: string
    description: string
    active: boolean
  }[]
  total_records: number
  total_pending: number
  total_abnormal: number
}

export type PnlSummary = {
  strategy_no: string
  realized_pnl: number
  unrealized_pnl: number
  fill_count: number
  position_count: number
}

export async function loadFullOverview(): Promise<FullOverview> {
  const response = await request('/api/business/overview/full')
  if (!response.ok) throw new Error('综合概览读取失败')
  return await response.json()
}

export async function validateStrategyFactors(strategyId: number): Promise<{
  status: string
  factors?: { name: string; weight: number }[]
  message: string
  missing_factors?: string[]
}> {
  const response = await request(`/api/business/strategy/${strategyId}/validate-factors`, {
    method: 'POST',
  })
  return await response.json()
}

export async function generateBacktestReport(taskId: number): Promise<{
  status: string
  report?: unknown
  message?: string
}> {
  const response = await request(`/api/business/backtest/${taskId}/generate-report`, {
    method: 'POST',
  })
  return await response.json()
}

export async function checkTradeRisk(instructId: number): Promise<{
  status: string
  blocking_rules?: unknown[]
  message?: string
}> {
  const response = await request(`/api/business/trade/${instructId}/risk-check`)
  return await response.json()
}

export async function generateTradeFill(instructId: number): Promise<{
  status: string
  fill?: unknown
  message?: string
}> {
  const response = await request(`/api/business/trade/${instructId}/generate-fill`, {
    method: 'POST',
  })
  return await response.json()
}

export async function loadPnlSummary(strategyNo: string): Promise<PnlSummary> {
  const response = await request(`/api/business/pnl/summary/${encodeURIComponent(strategyNo)}`)
  return await response.json()
}

export async function recentAudits(limit = 20): Promise<{
  records: unknown[]
  total: number
}> {
  const response = await request(`/api/business/audit/recent?limit=${limit}`)
  return await response.json()
}
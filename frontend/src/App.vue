<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">数字资产量化策略管理台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">策略员配置量化因子与回测参数，风控员按回测结果设定风控规则，交易员根据信号执行委托并在成交后核对盈亏核算。</span>
        <span class="head-user">当前值班：业务协作组</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "策略配置", path: "/strategy_config" }, { label: "因子库", path: "/factor_library" }, { label: "回测任务", path: "/backtest_task" }, { label: "回测报告", path: "/backtest_report" }, { label: "信号订阅", path: "/signal_sub" }, { label: "风控规则", path: "/risk_rule" }, { label: "持仓快照", path: "/position_snapshot" }, { label: "交易所绑定", path: "/exchange_binding" }, { label: "交易指令", path: "/trade_instruct" }, { label: "成交记录", path: "/trade_fill" }, { label: "盈亏核算", path: "/pnl_settle" }, { label: "资金流水", path: "/capital_journal" }, { label: "策略评审", path: "/strategy_review" }, { label: "组合配置", path: "/portfolio_alloc" }, { label: "再平衡执行", path: "/rebalance_exec" }, { label: "行情快照", path: "/market_snapshot" }, { label: "预警派发", path: "/alert_dispatch" }, { label: "操作审计", path: "/operation_audit" }]
</script>

# 数字资产量化策略管理台

策略员配置量化因子与回测参数，风控员按回测结果设定风控规则，交易员根据信号执行委托并在成交后核对盈亏核算。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              18个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 策略配置 | `strategy_config` | 策略单 | 策略名称、标的品种、参数集合 |
| 因子库 | `factor_library` | 因子定义 | 因子名称、计算周期、数据源类型 |
| 回测任务 | `backtest_task` | 回测单 | 策略编号、历史区间、初始本金 |
| 回测报告 | `backtest_report` | 报告单 | 回测编号、年化收益、最大回撤 |
| 信号订阅 | `signal_sub` | 信号单 | 策略编号、信号方向、触发价格 |
| 风控规则 | `risk_rule` | 风控单 | 策略编号、规则类型、阈值上限 |
| 持仓快照 | `position_snapshot` | 持仓单 | 标的代码、持有数量、成本均价 |
| 交易所绑定 | `exchange_binding` | 绑定单 | 交易所名称、密钥指纹、操作域 |
| 交易指令 | `trade_instruct` | 指令单 | 策略编号、标的代码、委托方向 |
| 成交记录 | `trade_fill` | 成交单 | 指令编号、成交价格、成交数量 |
| 盈亏核算 | `pnl_settle` | 核算单 | 策略编号、统计区间、已实现盈亏 |
| 资金流水 | `capital_journal` | 流水单 | 账户编号、变动类型、变动金额 |
| 策略评审 | `strategy_review` | 评审单 | 策略编号、实盘时长、评审结论 |
| 组合配置 | `portfolio_alloc` | 组合单 | 组合名称、成员策略、分配比例 |
| 再平衡执行 | `rebalance_exec` | 再平衡单 | 组合编号、执行时刻、调整方向 |
| 行情快照 | `market_snapshot` | 行情单 | 标的代码、最新价格、二十四小时涨跌 |
| 预警派发 | `alert_dispatch` | 预警单 | 预警类型、触发规则、当前数值 |
| 操作审计 | `operation_audit` | 审计单 | 操作类型、操作人员、操作内容 |

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：其它垂类行业
子方向：web3 区块链 量化交易

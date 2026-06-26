# 架构设计

## 技术栈
| 层 | 选型 |
|----|------|
| 后端 | Python 3.11 + FastAPI |
| 前端 | React + TypeScript + Vite |
| 数据 | akshare / baostock（A 股日线数据） |
| 数据存储 | SQLite（轻量、单用户场景） |
| 任务调度 | APScheduler（每日数据更新） |

## 系统组件

```
┌────────────────┐    HTTP     ┌────────────────┐
│   Frontend     │ ◄────────► │    Backend     │
│   (React)      │   REST API  │   (FastAPI)    │
└────────────────┘             └────────┬───────┘
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                    ┌──────────┐  ┌──────────┐  ┌──────────┐
                    │ Backtest │  │  Signal  │  │   Data   │
                    │  Engine  │  │ Computer │  │   Sync   │
                    └──────────┘  └──────────┘  └──────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │   akshare /  │
                                         │   baostock   │
                                         └──────────────┘
```

### Backend 模块
- **Data Sync**：每日从 akshare/baostock 拉取 ETF 日线
- **Backtest Engine**：接收 ETF 池 + 动量参数，运行历史回测，输出业绩指标
- **Signal Computer**：基于最新动量数据，生成当前调仓建议
- **API Layer**：FastAPI 路由（`/api/backtest`, `/api/signals`, `/api/etfs`）

### Frontend 模块
- **Dashboard**：当前动量排名 + 调仓建议
- **Backtest UI**：选择 ETF 池 + 参数，触发回测，查看业绩图表
- **ETF Pool Manager**：增删 ETF 池中的标的

## 数据模型

### ETF
```
id, code (e.g. "510300"), name, market (SH/SZ), category
```

### DailyPrice
```
code, date, open, high, low, close, volume
```

### BacktestRun
```
id, etf_pool, momentum_window, rebalance_freq, start_date, end_date,
metrics (json: sharpe, max_dd, annual_return), created_at
```

### SignalSnapshot
```
date, etf_code, momentum_score, rank, action (buy/sell/hold)
```

## 关键决策
- **动量因子**：默认 12-1 动量（最近 12 个月收益，剔除最近 1 个月）
- **调仓频率**：默认月度
- **ETF 池**：用户可编辑的列表，存 SQLite
- **回测缓存**：相同参数回测结果缓存 24 小时

## 目录布局
```
backend/
├── app/
│   ├── main.py
│   ├── api/             # FastAPI 路由
│   ├── core/            # 配置
│   ├── data/            # 数据同步
│   ├── backtest/        # 回测引擎
│   ├── signals/         # 信号计算
│   └── models/          # SQLAlchemy 模型
├── tests/
└── requirements.txt

frontend/
├── src/
│   ├── pages/
│   ├── components/
│   └── api/
├── package.json
└── vite.config.ts
```

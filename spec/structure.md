# 项目目录结构说明

## 架构选型

全栈架构：**React 前端 + Python 后端**（2026-06-28 决定）。

将原聚宽（JoinQuant）单文件策略 `main.py` 重构为前后端分离的应用。

### 职责划分

| 层 | 职责 | 技术 |
|---|------|------|
| **前端 (frontend/)** | 配置 UI：静态核心池、主题分类词典、策略参数；展示：回测结果、ETF 历史数据、当日买入/卖出信号、当前持仓 | React |
| **后端 (backend/)** | 提供 REST API；执行 ETF 筛选逻辑；收盘数据同步；对接行情数据源 | Python |

### 后续重构范围

- 原 `main.py` 的筛选/回测核心逻辑 → 迁移至 `backend/`（去除 JoinQuant API 依赖，封装为可独立调用的服务）
- 新增前端配置面板，替代原 `STRATEGY_CONFIG` 硬编码字典
- 主题词典 `THEME_KEYWORDS`、静态池 `STATIC_ETF_POOL` 等配置项由前端管理并持久化

## 当前结构

```
etf-momentum/
├── main.py                 # 原聚宽策略脚本（待重构）
├── backend/                # 后端服务（待开发）
├── frontend/               # React 前端（待开发）
├── spec/                   # 项目级 Spec
│   ├── requirements.md     # 整体需求（待补充）
│   ├── design.md           # 架构设计（待补充）
│   ├── tasks.md            # 里程碑任务（待补充）
│   ├── devlog.md           # 开发日志
│   └── structure.md        # 本文档
├── openspec/               # OpenSpec 配置
│   ├── specs/              # 长期规格
│   └── changes/            # 当前变更
├── AGENTS.md               # 开发规则（待安装）
└── .speccoding-state.json  # 工作流状态（待创建）
```
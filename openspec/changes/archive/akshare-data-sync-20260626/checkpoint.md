# Checkpoint: akshare-data-sync

- **阶段**: spec
- **进度**: spec.md + plan.md 已生成（31 项待执行）
- **活跃变更**: akshare-data-sync
- **分支**: feature/akshare-data-sync（基于 main）

## 已完成
- Stage 1 git branch
- Stage 2 proposal（已确认）
- Stage 3 brainstorming（4 项关键设计决策：Protocol+DI / dialect-agnostic upsert / 增量+full / log+skip）
- Stage 4 spec：spec.md（9 Requirements）+ plan.md（31 项 checkbox）

## 下一阶段
- Stage 5 executing：实现 akshare 数据同步脚本（按 plan.md 顺序 TDD）

## 备注
- akshare 真实调用需网络，测试用 FakeAkshareClient 替代
- 默认增量模式：start=None 时由 caller 指定；CLI 默认从一年前到今天

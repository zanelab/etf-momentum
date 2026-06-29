# akshare 代码归一化

## 背景

M9 接入 akshare 后出现代码格式不一致问题，影响 `filter_etfs` 合并 static + dynamic pool 时的正确性。

| 来源 | 格式 | 示例 |
|------|------|------|
| 静态池（`seed.py` / DB） | 6 位 + `.XSHG` / `.XSHE` 后缀 | `510300.XSHG`、`159915.XSHE` |
| **JoinQuant 原版动态池**（`main.py:131-133`） | `get_all_securities()` 返回**带后缀** | `510300.XSHG`、`159915.XSHE` |
| akshare `fund_etf_spot_em()` | 6 位裸码（无交易所字段） | `510300`、`159915` |
| akshare `fund_etf_hist_em(symbol=...)` | 接受 6 位裸码 | `510300` |
| `defensive_etf` 策略参数 | 带后缀 | `511880.XSHG` |

## 设计意图确认（对照 `main.py`）

用户提出「静态池与动态池的合并是否合理」是必要追问。读完 `main.py` 后结论清晰：

**1. 融合是显式设计** — `main.py:280-287`：

```python
# ==================== 池子融合 ====================
# 静态池 + 动态池，去重，并排除防御ETF
combined_pool = list(set(STATIC_ETF_POOL + g_dynamic_pool))
if config["defensive_etf"] in combined_pool:
    combined_pool.remove(config["defensive_etf"])

log.info(f"【筛选开始】静态池 {len(STATIC_ETF_POOL)}只 + 动态池 {len(g_dynamic_pool)}只 -> 融合池 {len(combined_pool)}只")
```

意图：静态池（精选核心宽基/行业/跨境）+ 动态池（每日按流动性筛选的全市场 ETF 前 N 名）做并集，统一进入后续均线过滤/动量评分。**融合 = 静态精选 + 全市场流动性补集**。

**2. 原版动态池就是带后缀的** — `main.py:131-133`：

```python
df_all_etf = get_all_securities(['etf'], date=context.current_dt)
all_etf_codes = df_all_etf.index.tolist()
```

JoinQuant 平台层在 `get_all_securities` 返回 index 时已经附加 `.XSHG/.XSHE` 后缀，所以原版 `g_dynamic_pool` 与 `STATIC_ETF_POOL` **字符串格式完全一致**，可以直接 `set()` 去重。

**3. akshare 引入的真正问题**：

| 步骤 | JoinQuant 时代 | akshare 时代 | 后果 |
|------|--------------|------------|------|
| 动态池拉取 | `get_all_securities` → `510300.XSHG` | `fund_etf_spot_em` → `510300` | DB 里裸码与静态池后缀格式并存 |
| `set(static + dynamic)` | 自动 dedupe | **同名 ETF 出现 2 次** | 浪费筛选次数；同一标的在 `score_list` 里可能出现两次，theme 分类结果不同 |
| `display_names[code]` 查 `static_pool` 表 | `510300.XSHG` 命中 | `510300` **查不到** | 动态池标的 theme 一律退化为「其他」，**行业分散逻辑在动态池标的上失效** |
| `defensive_etf in pool`（多处） | 命中 | 裸码 vs 后缀 → **不命中** | 防御 ETF 可能被误选入持仓 |

**结论**：合并**没有错**，错的是「动态池里的元素跟静态池不是同一字符串」。归一化就是修复这个语义一致性问题。

## 目标

在系统内**统一使用带后缀的规范格式**（`510300.XSHG`、`159915.XSHE`），所有外部输入（akshare 返回、用户提交）经规范化后入库/查询，所有下游消费（K 线、display_names、filter_etfs 合并、defensive 比对）都使用规范格式。

## 提议方案

### 1. 新增 `app/data_sources/codes.py` 规范化工具

```python
def normalize_etf_code(code: str) -> str:
    """Return canonical form: 'XXXXXX.XSHG' or 'XXXXXX.XSHE'.

    - Strip whitespace, uppercase.
    - If already has .XSHG/.XSHE suffix → return as-is (validated).
    - 6-digit numeric → infer exchange from first digit:
        5/6 → .XSHG; 1/0/3 → .XSHE; else raise ValueError.
    - Other formats → raise ValueError.
    """

def same_etf(a: str, b: str) -> bool:
    """True if both codes normalize to the same string."""
    return normalize_etf_code(a) == normalize_etf_code(b)
```

### 2. akshare `all_etf_entries` 返回规范格式

在 `AkShareSource.all_etf_entries` 里把返回的 code 经 `normalize_etf_code` 包装后再返回。动态池同步直接拿到规范格式入库，无需前端转换。

### 3. 静态池输入校验

`POST /api/configs/pool` 接受用户提交 code 时校验/规范化（保留兼容：接受裸码或带后缀，都存为带后缀）。

### 4. `filter_etfs` 合并前规范化

```python
pool = list({normalize_etf_code(c) for c in static_pool + dynamic_pool})
if normalize_etf_code(params.defensive_etf) in pool:
    pool.remove(normalize_etf_code(params.defensive_etf))
```

### 5. `load_display_names` 双查兜底

为兼容历史数据（极少数动态池条目可能仍为裸码），`load_display_names` 先按原 code 查，再用 `normalize_etf_code(code)` 查一遍。两条都返回 `{canonical_code: display_name}`。

### 6. 数据迁移

不需要专门迁移脚本 — 动态池同步（`POST /sync`）天然会把所有 code 重新规范化覆盖；存量 dynamic_pool_entry 表里如果有裸码 row，下次同步时同名（normalized 后相同）code 的 row 会被更新/合并。

策略：sync 时按 `normalize_etf_code(code)` 做 upsert key，保证不会出现「同一标的两个 row」。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 规范格式 | **带后缀**（`XXXXXX.XSHG/XSHE`） | 与现有静态池数据、defensive_etf 默认值、JoinQuant 原策略保持一致；语义更明确 |
| 推断交易所 | **首字符规则**（5/6→SH, 1/0/3→SZ） | A 股 ETF 公开惯例；akshare 不返回交易所字段 |
| 兼容旧数据 | **读时双查 + 写时归一** | 最小迁移成本；前端无感 |
| 实施范围 | **仅动态池路径 + filter_etfs 合并 + load_display_names** | akshare K 线本身接受裸码，无需改动；fixture / static_pool 路径已有规范格式 |
| 测试 | **新测试文件**：`test_codes.py`（normalize + same_etf + edge cases） + 扩展 `test_dynamic_pool_api.py`（sync 后 code 必为带后缀） | TDD 强制 |

## Trade-off

- **优点**：消除两个 pool 合并的语义不一致；主题分类对动态池生效；defensive ETF 比对稳定；akshare 仍是裸码但对系统透明
- **缺点**：增加 1 个工具模块 + 多处调用点；规则首字符推断有理论边界（如未来上交所发行 `1` 开头 ETF 则误判，但目前不存在）
- **不做的事**：不改 akshare K 线 API 调用格式（裸码已能工作）；不重写 fixture 文件（已是带后缀）；不做大规模历史数据回填

## 验收标准

- `normalize_etf_code("510300") == "510300.XSHG"`
- `normalize_etf_code("510300.XSHG") == "510300.XSHG"`
- `same_etf("510300", "510300.XSHG") is True`
- akshare sync 后 DB 中所有 `dynamic_pool_entry.code` 形如 `XXXXXX.XSHG/XSHE`
- `filter_etfs(static=[510300.XSHG], dynamic=[510300])` 合并后只 1 个候选（不是 2 个）
- `load_display_names(["510300"])` 与 `load_display_names(["510300.XSHG"])` 都能取到 display_name
- `params.defensive_etf = "511880"` 也能正确剔除（裸码兼容）
- 现有 116 个测试 + 新增测试全部通过

## 风险与回滚

- 风险：现有 dynamic_pool_entry 行（若有历史裸码）的 `code` 字段格式与新规不一致 — 但 sync 触发即自动更新；无破坏性
- 回滚：本次变更只新增工具函数 + 调用点替换；revert commit 即可

## 不在本次范围

- 定时自动同步（cron / APScheduler）— 单独迭代
- akshare `fund_etf_spot_em` 真实调用集成测试（mock 绕过网络）— 单独迭代
- akshare 代码归一化扩展到全市场股票（不只 ETF）— 后续视需求

---

**Status**: - [x] 提案已确认（2026-06-29）— 进入 spec 阶段
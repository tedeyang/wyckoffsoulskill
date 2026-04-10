---
name: wyckoff-vpa
description: Use when analyzing Chinese A-shares with Wyckoff/VPA, especially when intraday 5-minute confirmation, structured evidence output, and multi-timeframe context are required.
---

# Wyckoff Volume-Price Analysis (VPA)

Chinese A-share Wyckoff analysis with evidence-first JSON output. Prefer this when the user asks to analyze a stock, compare structure across daily/weekly/higher timeframes, or wants intraday confirmation from 5-minute bars.

## Quick Start

```bash
# 推荐入口
python vpa.py resolve "华统股份"
python vpa.py analyze "华统股份"
python vpa.py analyze "中信证券" --pretty
python vpa.py analyze "600519" --analysis-mode deep --full

# 兼容入口
python akshare_fetcher.py analyze "华统股份" --pretty
```

## What The Engine Returns

Current schema version: `1.0.1`

Primary sections:

- `key_levels`
- `raw_market_facts`
- `structural_context`
- `event_candidates`
- `swing_comparisons`
- `effort_result`
- `absorption_and_acceptance`
- `point_and_figure_summary`
- `inference_inputs`
- `llm_digest`

Do not rely on removed legacy fields such as `trend`, `phase`, `probabilities`, or `optional_legacy_outputs`.

## Core Rules

1. 优先使用 `5分钟` 做执行确认；若分钟数据缺失，必须明确降级并降低置信度。
2. 先讲证据，再讲结论。不要跳过 `event_candidates / effort_result / absorption_and_acceptance`。
3. 输出威科夫术语时使用中文名称，如：
   - `Spring` → `弹簧`
   - `Shakeout` → `震仓`
   - `SOS` → `强势征兆`
   - `UT` → `上冲`
   - `UTAD` → `上冲后派发`
   - `SOW` → `弱势征兆`
4. 盘中分析必须优先看 `raw_market_facts.live_session`，不要把前一日收盘误当成现价。
5. 周线和更高周期背景优先看：
   - `structural_context.weekly_context`
   - `structural_context.higher_timeframe_context.monthly_context`
   - `structural_context.multi_timeframe_alignment`

## Preferred Reading Order

### 1. 先看快照

- `key_levels.current`
- `raw_market_facts.live_session.is_live_session`
- `raw_market_facts.minute_last_day`
- `structural_context.trading_range.current_position_pct`

### 2. 再看背景

- `structural_context.weekly_context`
- `structural_context.higher_timeframe_context.monthly_context`
- `structural_context.multi_timeframe_alignment`

### 3. 再看事件与证据

从 `event_candidates` 中优先筛选：

- `candidate = true`
- `score` 最高的 3-6 个
- 结合 `timeframe`
- 阅读 `evidence`

### 4. 再看行为质量

- `effort_result.high_volume_no_progress`
- `effort_result.low_volume_pullback`
- `effort_result.effort_result_divergence`
- `absorption_and_acceptance.*`

### 5. 最后看摘要

- `point_and_figure_summary`
- `llm_digest`

`llm_digest` 适合快速输出，但不要忽略上面的证据层。

## 5-Minute Confirmation Rules

- 偏多确认：`close_position > 0.60` 且 `vs_vwap = above`
- 偏空确认：`close_position < 0.40` 且 `vs_vwap = below`
- 中性：`0.40 ~ 0.60`

同时结合：

- `gap_pct` 与 `gap_filled`
- `supply_bars / demand_bars`
- 日内高低点是否失守

## Output Style

### 专业模式

默认输出简洁的专业结论，基于证据包：

- 当前位置
- 多周期背景
- 主导事件
- 5分钟确认
- 风险与交易含义

### 说人话模式

当用户说“说人话 / 看不懂 / 简单点 / 新手”等时：

- 200 字以内
- 不出现 `Spring / UTAD / VWAP / TR / POC` 等术语
- 必须包含：
  - 能不能买
  - 止损
  - 目标
  - 风险

## Compact Output

默认 CLI 是 compact 模式，适合终端和 LLM：

- `event_candidates` 只保留候选或高分事件
- `swing_comparisons` 只保留最近一段
- 使用 `--full` 获取完整证据包

## Deep Mode

`--analysis-mode deep` 会拉更长周期数据，但输出 schema 不变。仍然优先看：

- `weekly_context`
- `monthly_context`
- `multi_timeframe_alignment`

## What To Avoid

- 不要再引用 `trend / phase / probabilities`
- 不要把原始 P&F `columns` 长列表直接当作主要输入
- 不要在用户要求“说人话”时堆术语
- 不要忽略盘中 `live_session`

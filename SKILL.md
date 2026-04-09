---
name: wyckoff-vpa
description: Wyckoff VPA analysis for Chinese A-shares - high-speed parallel data fetch, multi-timeframe analysis with detailed intraday interpretation
---

# Wyckoff Volume-Price Analysis (VPA)

High-speed Wyckoff analysis for Chinese A-shares. **Execution time: ~1.3s** via parallel Sina data sources.

⚠️ **CRITICAL RULE**: 5-Minute analysis is **MANDATORY** for entry/exit confirmation.

## Quick Start

```python
from akshare_fetcher import quick_analysis, resolve_stock_code

# 支持股票名称、简称、代码查询
result = resolve_stock_code("通富微电")  # 返回: {'code': '002156', 'name': '通富微电', ...}
result = resolve_stock_code("茅台")      # 返回: {'code': '600519', 'name': '贵州茅台', ...}
result = resolve_stock_code("002840")    # 返回: {'code': '002840', 'name': '华统股份', ...}

# 模糊匹配返回多个结果时需要用户确认
# 返回: {'matches': [('002156', '通富微电'), ('688123', '其他微电')], 'requires_clarification': True}

# 执行分析
analysis = quick_analysis("002156")
```

### 股票代码查询

支持以下查询方式：
1. **完整名称**: `通富微电` → `002156`
2. **简称/别名**: `茅台` → `贵州茅台` → `600519`
3. **标准代码**: `002156` → `002156`
4. **带前缀代码**: `sh600519` / `sz002156`

**多匹配处理**: 如果查询返回多个可能股票，AI 应向用户展示列表并请求确认。

## Data Source

**Sina** for daily/weekly/minute (parallel fetch, ~1.3s total)

## Three-Timeframe Analysis (REQUIRED)

**Weekly** → Validates major trend and S/R levels  
**Daily** → Identifies Wyckoff Phase and TR position  
**5-Minute** → Mandatory execution confirmation

### 5-Minute Confirmation Rules

- **Long**: Close >60% + gap up NOT filled + above VWAP
- **Short**: Close <40% + gap down NOT filled + below VWAP
- **No Trade**: Close 40-60% (indecision)

## AI Analysis Requirements

### 1. Reciprocal Multi-Timeframe Analysis

```
【大级别→小级别验证】
周线位置: [X]% → [support/resistance/neutral]
日线位置: [Y]% → [Phase A/B/C/D]
5分钟位置: [Z]% → [bullish/bearish/neutral]
```

### 2. Last Day Minute Analysis

```
【最后交易日详细拆解】
日期: [YYYY-MM-DD]
开盘跳空: [gap_pct]% [filled/unfilled]
全天区间: ¥[low] ~ ¥[high]
收盘位置: [X]% of range ([day_type])
VWAP: ¥[vwap] ([above/below])
供需柱: 供应[N]根 | 需求[N]根 (主导: [dominant])
```

### 3. Event Probability

```
【事件概率评估】
Spring概率 (5天): [X]%
向上突破 (10天): [Y]%
Distribution (5天): [Z]%
趋势延续: [W]%
```

### 4. Action Hypothesis

```
【行动假设指南】

假设1: [情景] (概率[X]%)
  触发: [条件]
  行动: [买入/卖出/观望]
  止损: ¥[price]
  目标: ¥[price]

当前建议:
  持仓者: [建议]
  空仓者: [建议]
```

### 5. Report Output Format (REQUIRED)

```
═══════════════════════════════════════════════════════════════
威科夫分析报告 | [Symbol] | ¥[Price]
═══════════════════════════════════════════════════════════════

📌 一句话归纳: [用通俗语言概括当前状态、关键信号和操作建议，50-80字]

【威科夫价位缩略图 + 点数图测算】
[用ASCII字符画出箱体区间+关键价位，点数图只输出测算结果]

【价位分布图】
      ¥48.26 ─┬─ TR高点 ───────────────────────
              │
      ¥46.82 ─┤────── Value Area High (压力位)
    ╔═════════╧═════════╗
    ║  POC: ¥46.51      ║
    ║                   ║
    ║  ← 当前价 ¥44.74  ║ ← 价格位置(用箭头标出)
    ║                   ║
    ╚═════════╤═════════╝
      ¥40.68 ─┤────── Value Area Low (支撑位)
              │
      ¥40.40 ─┴─ TR低点 ───────────────────────

【点数图 (P&F) 测算 - Box=1%xLTP, 3格反转, 200日回看】
当前: [X/O]列[N]格 | 盘整区: [M]列×[H]boxes @ ¥[low]~¥[high]

    ┌────────────────────────────────────────────────────┐
    │  预测目标 (横向计数法)                              │
    ├────────────────────────────────────────────────────┤
    │  中性目标: ¥[price] (+[X]%)  ← [说明]              │
    │  激进目标: ¥[price] (+[X]%)  ← [说明]              │
    │  看跌目标: ¥[price] (-[X]%)  ← [说明/无]           │
    └────────────────────────────────────────────────────┘

【数据质量详情】
日线数据: [N] 根 | [YYYY-MM-DD] ~ [YYYY-MM-DD]
周线数据: [N] 根 | [YYYY-MM-DD] ~ [YYYY-MM-DD]
5分钟数据: [N] 根 | [YYYY-MM-DD HH:MM] ~ [YYYY-MM-DD HH:MM]
数据获取耗时: [X]ms
```

## Key Principles

1. **5-minute is MANDATORY** - Never trade without intraday confirmation
2. **Reciprocal validation** - Weekly/Daily/5min must align for high-confidence trades
3. **Probability, not certainty** - Express all forecasts as probabilities
4. **Hypothesis-driven** - Define clear entry/stop/target before trading
5. **Volume confirms** - Price action without volume support is suspect
6. **Risk first** - Define invalidation level before entry

---

## Code vs AI Division

| Component | Code Execution (~1.3s) | AI Analysis (<0.01s) |
|-----------|------------------------|----------------------|
| Data fetching | Sina API parallel calls | - |
| Indicators | MA, TR, VWAP, Volume Profile | - |
| Pattern recognition | - | Spring/Upthrust identification |
| Interpretation | - | Multi-timeframe synthesis |
| Recommendation | - | Hypothesis generation |

**Total: ~1.3s** (<2s requirement ✅)

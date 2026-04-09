---
name: wyckoff-vpa
description: Wyckoff VPA analysis for Chinese A-shares - high-speed parallel data fetch, multi-timeframe analysis with detailed intraday interpretation
---

# Wyckoff Volume-Price Analysis (VPA)

High-speed Wyckoff analysis for Chinese A-shares. **Execution time: ~1.3s** via parallel Sina data sources.

⚠️ **CRITICAL RULE**: 5-Minute analysis is **MANDATORY** for entry/exit confirmation.

## Installation

```bash
pip install -r requirements.txt
```

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

## Analysis Modes

### Standard Mode (默认)
- **日线**: 200 根 (~10个月)
- **周线**: 100 根 (~2年)
- **适用**: 波段交易、中期持仓

### Deep Mode (深度/长线分析)
触发关键词: `长线分析`、`深度研究`、`重度分析`、`long`、`deep`

- **日线**: 500 根 (~2年)
- **周线**: 200 根 (~4年)
- **适用**: 长期投资、大周期结构识别
- **AI 要求**: 必须进行多周期结构转换的深度解读

```python
# 深度分析调用
result = quick_analysis("600519", analysis_mode="deep")
```

## Data Source

**Sina** for daily/weekly/minute (parallel fetch, ~1.3s for standard, ~2s for deep)

## Three-Timeframe Analysis (REQUIRED)

**Weekly** → Validates major trend and S/R levels  
**Daily** → Identifies Wyckoff Phase and TR position  
**5-Minute** → Mandatory execution confirmation

### 5-Minute Confirmation Rules

- **Long**: Close >60% + gap up NOT filled + above VWAP
- **Short**: Close <40% + gap down NOT filled + below VWAP
- **No Trade**: Close 40-60% (indecision)

## Output Style Adaptation (输出风格自适应)

### 自动检测用户偏好

AI 必须根据用户的用词和反馈自动调整输出风格：

#### 专业分析模式 (默认)
触发条件: 用户未表达困惑，或使用专业术语如"分析一下"、"看看走势"

输出: 完整威科夫分析报告，包含所有技术细节

#### 简化通俗模式
触发关键词:
- "看不懂"、"说人话"、"太复杂"、"简单点"
- "什么意思"、"看不懂啊"、"能不能通俗点"
- "小白"、"新手"、"不懂"、"解释一下"

输出要求:
1. **字数限制**: 200字以内
2. **语言风格**: 大白话，避免术语
3. **必含内容**:
   - 当前股价和位置 (高位/低位/中间)
   - 能不能买 (能/不能/再等等)
   - 止损位 (跌到哪该跑)
   - 目标价 (涨到哪该卖)
4. **禁止内容**: Phase、Spring、TR、POC、VWAP等术语

简化版示例:
```
云天化现在¥33.28，处于近两年底部区域，比历史高点¥61腰斩了。

【能买吗？】可以轻仓试试，但别重仓。
【止损】跌破¥31就认输跑路。
【目标】涨到¥39-40可以卖，能赚18%左右。
【风险】现在还是下跌趋势，属于抄底，可能继续跌。
```

---

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

### 5. Deep Analysis Multi-Cycle Interpretation (深度分析专用)

当 `analysis_mode="deep"` 时，AI 必须进行以下多周期转换深度解读：

```
【大周期→小周期结构嵌套分析】

月线/季线背景 (通过200周线推导):
  大周期趋势: [bullish/bearish/sideways]
  主要TR区间: ¥[low] ~ ¥[high] (宽度[X]%)
  当前处于大周期位置: [X]% → [accumulation/distribution/markup/markdown]

周线中期结构 (200周):
  中期TR数量: [N]个 identifiable trading ranges
  关键突破/跌破点: [list key levels]
  中期Wyckoff阶段: [Phase]

日线当前结构 (500日):
  与周线TR的嵌套关系: [当前日线TR位于周线TR的X%位置]
  小周期Spring/Upthrust验证: [yes/no with evidence]
  多周期共振评估: [high/medium/low confidence]

结构转换预测:
  大周期突破条件: ¥[price] + volume > [X]
  时间窗口: [N] weeks/days
  转换概率: [X]%
```

## Report Output Format (美观排版规范)

### 排版原则

1. **使用 emoji 图标**增强可读性：📊 💡 ⚠️ 🎯 📈 📉 ✅ ❌
2. **紧凑格式**：表格不要太宽，使用简单对齐
3. **视觉分隔**：使用分隔线和空行区分不同模块
4. **关键信息突出**：价格、百分比、操作信号用 **粗体**
5. **颜色暗示**（A股市场：红涨绿跌）：
   - 上涨/看涨：🔴 ↑ +N%
   - 下跌/看跌：🟢 ↓ -N%
   - 中性/观望：⚪ →

### 标准报告格式

```
╔══════════════════════════════════════════════════════════════╗
║ 📊 威科夫分析报告 │ [股票] ([代码]) │ ¥[价格] ([涨跌]%)      ║
╚══════════════════════════════════════════════════════════════╝

💡 一句话总结
──────────────────────────────────────────────────────────────
[50-80字概括：位置+趋势+关键信号+操作建议]


📈 关键价位
──────────────────────────────────────────────────────────────
当前价格   │ ¥[价格] ([涨跌]%)
区间位置   │ [X]% ([低/中/高位])
区间范围   │ ¥[低] ~ ¥[高] (宽[X]%)
关键位     │ 支撑 ¥[支撑] / 压力 ¥[压力]
均线       │ MA5:¥[5] / MA10:¥[10] / MA20:¥[20]

趋势: **[涨/跌/震荡]** │ 阶段: **[Phase X]** │ 信号: **[Spring/Upthrust]**


🎯 点数图目标 (Box=¥[X], 当前[X/O]列[N]格)
──────────────────────────────────────────────────────────────
类型        价格       涨跌幅     说明
──────────  ─────────  ─────────  ──────────────────
🔴 中性    ¥[价格]    +[X]%     盘整区测幅
🔴 激进    ¥[价格]    +[X]%     1.5倍延伸
🟢 看跌    ¥[价格]    -[X]%     [如有]


📊 概率评估
──────────────────────────────────────────────────────────────
事件                    概率      解读
──────────────────────  ────────  ──────────────────────────
Spring (5天)            [X]%      [高/中/低]概率反弹
向上突破 (10天)         [X]%      [高/中/低]概率突破
Distribution (5天)      [X]%      [高/中/低]概率派发
趋势延续                [X]%      趋势持续可能性


⚡ 行动建议
──────────────────────────────────────────────────────────────
【持仓者】[建议] 止损: ¥[价格]
【空仓者】[建议] 入场:¥[价格] → 目标:¥[价格] → 止损:¥[价格]


⚠️ 风险提示
──────────────────────────────────────────────────────────────
• [风险点1]
• [风险点2] 
• [风险点3]


📋 数据新鲜度: 日线[N]根 ([日期]) │ 周线[N]根 ([日期]) │ [X]ms
```

### 简化版格式 (说人话模式)

```
╔══════════════════════════════════════════════════════════════╗
║ [股票] ([代码]) │ ¥[价格] ([涨跌]%)                          ║
╚══════════════════════════════════════════════════════════════╝

[股票]现在¥[价格]，处于[位置描述]。

【能买吗】[能/不能/再等等] [理由]
【止损】跌破¥[价格]就跑路
【目标】涨到¥[价格]可以卖，赚[X]%
【风险】[主要风险]
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

# Wyckoff VPA Skill v1.0.1

威科夫量价分析 (Wyckoff Volume-Price Analysis) Skill for Chinese A-shares.

> **"The market is a device for transferring money from the impatient to the patient."** — Warren Buffett
> 
> **" tape reading is the art of determining the moment when a stock is ready to move."** — Richard D. Wyckoff

---

## 🚀 使用示范

### 对话中使用

作为 AI Skill，你可以直接在对话中要求分析股票：

```
用户: 分析股票通富微电
AI: [执行威科夫分析，输出完整报告]

用户: 深度研究云天化
AI: [切换至深度模式，500日/200周线，大周期结构分析]

用户: 看一下茅台的走势
AI: [标准模式分析，200日/100周线]
```

### 使用示例

#### 示例 1: 标准分析（证据优先）

**对话输入:**
```
分析中国中免
```

**AI 输出:**
```
{
  "schema_version": "1.0.1",
  "key_levels": {
    "current": 67.89,
    "tr_position_pct": 18.4
  },
  "structural_context": {
    "weekly_context": {
      "current_position_pct": 21.3
    },
    "multi_timeframe_alignment": {
      "label_zh": "部分同向"
    }
  },
  "llm_digest": {
    "compact_take": "偏空但接近区间低位，需等待5分钟确认。",
    "event_stack": [
      {
        "name": "弹簧",
        "timeframe": "daily",
        "score": 0.78
      }
    ]
  }
}
```

#### 示例 2: 深度分析（长线投资）

**对话输入:**
```
深度研究云天化
```

**AI 输出:**
```
{
  "schema_version": "1.0.1",
  "structural_context": {
    "weekly_context": {
      "current_position_pct": 14.96
    },
    "higher_timeframe_context": {
      "monthly_context": {
        "current_position_pct": 16.42
      }
    }
  },
  "event_candidates": [
    {
      "event_code": "Spring",
      "name": "弹簧",
      "timeframe": "daily",
      "score": 0.81
    }
  ],
  "llm_digest": {
    "compact_take": "周线和更高周期都在低位，若5分钟回到强势区可继续跟踪。"
  }
}
```

#### 示例 3: 模糊查询

**对话输入:**
```
分析一下隆基
```

**AI 处理:**
```
找到多个匹配，请确认：
1. 隆基绿能 (601012) - 光伏龙头
2. 隆基机械 (002363) - 汽车零部件

请回复序号或完整名称。
```

**用户:** `1` 或 `隆基绿能`

**AI:** [执行分析...]

---

### 💬 说人话模式 (自动切换)

如果你说以下关键词，AI 会自动输出**简化版**（200字以内，大白话）：

```
"说人话" / "看不懂" / "太复杂" / "简单点" 
"小白" / "新手" / "什么意思" / "解释一下"
```

**简化版示例：**

```
云天化现在¥33.28，处于近两年底部，比历史高点¥61腰斩了。

【能买吗？】可以轻仓试试，但别重仓。
【止损】跌破¥31就跑路。
【目标】涨到¥39-40可以卖，赚18%左右。
【风险】现在还是下跌趋势，抄底可能被套。
```

**简化版特点：**
- ✅ 不说术语（没有弹簧、上冲后派发、TR、POC）
- ✅ 直接告诉能不能买
- ✅ 给明确的止损和目标价  
- ✅ 风险说在前头
- ✅ 200字以内，一目了然

---

## 📚 威科夫方法论简介

### 核心思想

威科夫方法（Wyckoff Method）由 Richard D. Wyckoff 在20世纪初创立，是一套基于**供需关系**、**因果关系**和**相对强弱**的技术分析体系。

#### 三大定律

| 定律 | 含义 | 交易启示 |
|-----|------|---------|
| **供需关系** | 价格由供需力量对比决定 | 成交量确认价格行为 |
| **因果关系** | 横盘区间(TR)是"因"，后续趋势是"果" | 测量TR宽度预测目标价 |
| **相对强弱** | 个股相对于大盘的表现 | 选择强于大盘的个股 |

#### 市场周期四阶段

```
    价格
     ↑
  D  │        ┌─────┐  ← Distribution (派发)
  I  │       /       \     大户出货给散户
  S  │      /         \
  T  │     /           \
  R  │    /    C       \   ← Markdown (下跌)
  I  │   /    U         \      散户恐慌抛售
  B  │  /    M           \
  U  │ /    U             \
  T  │/    L               \____
  I  │    A                      ← Accumulation (吸筹)
  O  │   T                            大户收集筹码
  N  │  I
     │ /    M   ← Markup (上涨)
     │/     A        大户拉抬出货
     └───────────────────────→ 时间
```

#### Wyckoff Phase (交易区间内部阶段)

```
Phase A: 停止前期趋势, 初步支撑/压力测试
    ↓
Phase B: 构建原因 (机构吸筹/派发)
    ↓
Phase C: 测试供应/需求 (Spring/Upthrust)
    ↓
Phase D: 突破区间, 确认趋势转换
    ↓
Phase E: 进入新趋势 (Markup/Markdown)
```

---

## ✨ Features

- **智能股票查询**: 支持名称/简称/代码模糊查询 (5499只A股全覆盖)
- **双模式分析**: 
  - **Standard**: 200日/100周线，适合波段交易 (~1s)
  - **Deep**: 500日/200周线，适合长线投资 (~1.2s)
- **三周期共振**: 周线(趋势定位) + 日线(阶段识别) + 5分钟(执行确认)
- **点数图测算**: Box=1%×LTP, 3格反转，横向计数预测目标价
- **威科夫价位缩略图**: ASCII可视化TR区间、Value Area、关键价位
- **AI驱动报告**: 一句话归纳 + 多周期深度解读 + 行动假设

---

## 📦 Installation

### Using requirements.txt (Recommended)

```bash
pip install -r requirements.txt
```

### Manual Installation

```bash
pip install akshare>=1.10.0 pandas>=1.5.0 numpy>=1.21.0
```

---

## 🚀 Quick Start

### CLI JSON API (Recommended)

```bash
# 推荐入口
python vpa.py resolve "通富微电"
python vpa.py analyze "002156"
python vpa.py analyze "600519" --analysis-mode deep --pretty
python vpa.py analyze "600519" --analysis-mode deep --full

# 兼容入口

# ========== Step 1: 股票代码查询（返回 resolve_stock_code 同结构 JSON）==========

python akshare_fetcher.py resolve "通富微电"
python akshare_fetcher.py resolve "茅台"
python akshare_fetcher.py resolve "002840"
python akshare_fetcher.py resolve "SH600519"

# 模糊查询（requires_clarification=true）
python akshare_fetcher.py resolve "科技"

# ========== Step 2: 执行分析（默认 compact JSON，避免终端截断）==========

# 标准模式（默认）
python akshare_fetcher.py analyze "002156"

# 深度模式
python akshare_fetcher.py analyze "600519" --analysis-mode deep

# 便于阅读的格式化输出
python akshare_fetcher.py analyze "600519" --analysis-mode deep --pretty

# 需要完整证据包时使用 --full
python akshare_fetcher.py analyze "600519" --analysis-mode deep --full
```

### Command Line

```bash
# 标准分析
python akshare_fetcher.py analyze "中国中免"

# 深度分析
python akshare_fetcher.py analyze "茅台" --analysis-mode deep

# 代码解析
python akshare_fetcher.py resolve "隆基"
```

---

## 📊 证据包解读指南

### 1. `key_levels`

```python
{
    'current': 44.74,          # 当前价格
    'tr_low_20d': 40.4,        # 20日TR低点
    'tr_high_20d': 48.26,      # 20日TR高点
    'tr_position_pct': 55.2,   # 当前在TR中的位置 (0-100%)
    'ma5': 42.35,
    'ma10': 42.32,
    'ma20': 43.62,
}
```

这是轻量摘要层，用来快速看：

- 现价
- 近 20 日区间位置
- 近端均线位置

### 2. `structural_context`

```python
{
    'trading_range': {
        'high': 48.26,
        'low': 40.4,
        'current_position_pct': 55.2,
    },
    'weekly_context': {
        'current_position_pct': 26.22,
    },
    'higher_timeframe_context': {
        'monthly_context': {
            'current_position_pct': 31.8,
        }
    },
    'multi_timeframe_alignment': {
        'label': 'partially_aligned',
        'label_zh': '部分同向'
    }
}
```

这是背景层，决定你是在区间低位、中位还是高位，以及日/周/月有没有同向。

### 3. `event_candidates`

```python
[
    {
        'event_code': 'Spring',
        'name': '弹簧',
        'timeframe': 'daily',
        'candidate': True,
        'score': 0.82,
        'price_zone': {'low': 40.4, 'high': 41.2},
        'evidence': ['下破支撑后收回区间', 'close_quality=0.81，volume_ratio=1.24']
    }
]
```

事件层现在是核心输入，不再先给 `phase/probabilities`。

### 4. `effort_result` 与 `absorption_and_acceptance`

```python
{
    'effort_result': {
        'high_volume_no_progress': True,
        'low_volume_pullback': False,
        'effort_result_divergence': 0.63,
    },
    'absorption_and_acceptance': {
        'supply_absorption_score': 0.54,
        'breakout_acceptance_score': 0.0,
        'breakout_rejection_score': 0.21,
    }
}
```

这层主要回答：

- 放量有没有换来有效推进
- 回踩是良性还是转弱
- 突破后有没有形成接受

---

## 🎯 实战示例

### 示例1: 通富微电 (002156) - Spring交易

```bash
python vpa.py analyze "002156" --pretty

# 关键信号:
# - TR位置: 55.2%
# - 弹簧: candidate=true
# - 周线位置: 26.22% (周线底部)
# - 5分钟回到 VWAP 上方再算确认

# 交易计划:
# 触发: 突破¥46.82 (VA High)
# 止损: ¥42.00 (-6.1%)
# 目标: ¥48.64 (P&F中性) / ¥50.67 (激进)
# 盈亏比: 1:1.5 (中性) / 1:2.2 (激进)
```

### 示例2: 云天化 (600096) - 大周期反转

```bash
python vpa.py analyze "600096" --analysis-mode deep --pretty

# 深度分析关键发现:
# - 日线: 500根 (2年数据)
# - 周线: 200根 (4年数据)
# - 周线位置: 14.96% (大周期底部)
# - 月线位置: 16.42% (同步低位)
# - 多周期对齐: 部分同向
# - 顶层事件: 弹簧 / 测试 / 强势征兆

# 交易计划:
# 触发: 日线突破关键阻力并且 5 分钟回到强势区
# 止损: ¥30.5 (-8.3%)
# 目标: ¥39.6 / ¥42 / ¥45 (分批止盈)
# 持有周期: 3-6个月 (大周期持仓)
```

### 示例3: CLI快速分析

```bash
# 标准分析 - 快速判断
$ python vpa.py analyze "隆基"
# 输出 JSON：包含 key_levels / structural_context / event_candidates / llm_digest

# 深度分析 - 长线布局
$ python vpa.py analyze "隆基" --analysis-mode deep --pretty
# 输出 JSON：默认 compact 模式，使用 --full 获取完整证据包
```

---

## 📖 威科夫交易检查清单

### 买入前检查 (3-5分钟确认)

```
☐ 日线区间位置处于低位或中低位
☐ 周线/更高周期不在高位压制区
☐ 5分钟收盘>60% of range 且站上 VWAP
☐ 证据层出现弹簧 / 测试 / 强势征兆
☐ 盈亏比 > 3:1
☐ 明确止损位 (TR低点下方)
```

### 卖出前检查

```
☐ 日线区间位置处于高位
☐ 周线位置 > 70%
☐ 5分钟收盘<40% of range 且位于 VWAP 下方
☐ 证据层出现上冲 / 上冲后派发 / 弱势征兆
☐ 成交量在高位放大 (派发迹象)
```

---

## 🔧 高级用法

### 自定义分析参数

```bash
# 标准 vs 深度模式对比
python vpa.py analyze "600519" > /tmp/standard.json
python vpa.py analyze "600519" --analysis-mode deep > /tmp/deep.json

# 用 jq 对比关键字段
jq '.key_levels.tr_position_pct, .structural_context.weekly_context.current_position_pct' /tmp/standard.json
jq '.key_levels.tr_position_pct, .structural_context.weekly_context.current_position_pct' /tmp/deep.json
```

### 批量分析

```bash
for stock in 茅台 宁德时代 比亚迪; do
  python vpa.py analyze "$stock" | jq -c '{symbol,tr_pos:.key_levels.tr_position_pct,weekly_pos:.structural_context.weekly_context.current_position_pct,top_event:.llm_digest.event_stack[0].name}'
done
```

---

## ⚠️ 免责声明

1. **技术分析局限性**: 威科夫方法基于历史价格和成交量，不能保证未来表现。
2. **市场风险**: 股票市场存在系统性风险，任何分析方法都可能失效。
3. **个人判断**: 本工具提供分析框架，最终交易决策需结合基本面、市场环境和个人风险承受能力。
4. **数据延迟**: 行情数据可能存在延迟，不适用于高频交易决策。

**使用建议**: 
- 将本工具作为**决策支持系统**，而非自动交易系统
- 结合基本面分析 (财务报表、行业趋势)
- 严格执行止损纪律
- 保持概率思维，接受单笔亏损

---

## 📚 学习资源

### 威科夫经典著作
- Richard D. Wyckoff - "Studies in Tape Reading"
- Richard D. Wyckoff - "Stock Market Technique"

### 现代解读
- David Weis - "Trades About to Happen"
- Jack K. Hutson - "Charting the Stock Market"

### 推荐学习路径
1. **基础**: 理解TR、Spring、Upthrust基本概念
2. **进阶**: 学会读 `event_candidates / effort_result / absorption`
3. **实战**: 结合 5 分钟确认和周/月背景
4. **精通**: 多周期共振分析 + 资金管理

---

## Data Source

- **Sina Finance** - 日线/周线/分钟线数据

## License

MIT

---

**Star this repo if you find it helpful! ⭐**

For issues and feature requests, please use GitHub Issues.

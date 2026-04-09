# Wyckoff VPA Skill v0.5.1

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

#### 示例 1: 标准分析（波段交易）

**对话输入:**
```
分析中国中免
```

**AI 输出:**
```
## 威科夫分析报告 | 601888 中国中免 | ¥67.89 (-3.0%)

📌 一句话归纳: 中国中免处于Phase A潜在Spring区，TR位置1.1%触及区间低点，
强势下跌趋势中，建议观望等待止跌信号...

【关键价位】
  当前价格: ¥67.89 (-3.0%)
  TR区间: ¥67.79 ~ ¥76.5 (宽度12.8%)
  TR位置: 1.1% ⚠️ 区间极低位
  MA5/10/20: ¥68.96 / ¥69.98 / ¥71.52 (空头排列)

【趋势与阶段】
  趋势: strong_bearish
  阶段: Phase A - Potential Spring Zone

【点数图测算】
  看涨目标: ¥81.56 (+20.1%) / ¥84.62 (+24.6%)

【建议】
  持仓者: 跌破¥67.79考虑止损
  空仓者: 强烈观望，不宜抄底
```

#### 示例 2: 深度分析（长线投资）

**对话输入:**
```
深度研究云天化
```

**AI 输出:**
```
## 威科夫深度分析报告 | 600096 云天化 | ¥33.28
## 分析模式: 深度研究 | 日线:500根 (~2年) | 周线:200根 (~4年)

📌 一句话归纳: 云天化周线TR位置14.96%+日线15.51%形成强累积共振，
500日大周期底部结构显现，Spring概率55%，建议关注¥36.6突破...

【大周期结构 - 4年回顾】
  2022-2023: Distribution Phase (¥61→¥35)
  2023-2024: Markdown Phase (¥35→¥21) 
  2024-至今: Accumulation Phase A (¥21→¥33) ⚡当前⚡

【多周期共振】
  周线: 14.96% (大周期底部)
  日线: 15.51% (中期底部)
  共振评估: strong_accumulation (高置信度)

【点数图测算 - 500日】
  盘整区: ¥36.6~¥37.92
  看涨目标: ¥39.57 (+18.9%) / ¥41.06 (+23.4%)

【结构转换预测】
  大周期突破条件: 站稳¥45.1 + 成交量>1.5倍均量
  时间窗口: 3-6个月
  转换概率: 55%

【建议】
  持仓者: 继续持有，止损¥30.5
  空仓者: 可轻仓试多，突破¥36.6加仓
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
- ✅ 不说术语（没有 Phase、Spring、TR）
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

# 需要完整原始结构（等同 quick_analysis_v2 返回）时使用 --full
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

## 📊 报告解读指南

### 1. 关键价位 (Key Levels)

```python
{
    'current': 44.74,          # 当前价格
    'tr_low_20d': 40.4,        # 20日TR低点
    'tr_high_20d': 48.26,      # 20日TR高点
    'tr_position_pct': 55.2,   # 当前在TR中的位置 (0-100%)
    'ma5': 42.35,              # 5日均线
    'ma10': 42.32,             # 10日均线
    'ma20': 43.62,             # 20日均线
}
```

**原理说明**: 
- **TR (Trading Range)**: 威科夫核心概念，价格横盘区间代表供需平衡
- **TR位置**: <30% 为累积区(Spring区), >70% 为派发区(Upthrust区)
- **均线排列**: MA5>MA10>MA20 且价格>MA5 为多头排列，反之亦然

### 2. 成交量分布 (Volume Profile)

```python
{
    'poc': 46.51,              # Point of Control - 成交量最大价格
    'value_area_low': 40.68,   # 价值区低点 (70%成交量区间下沿)
    'value_area_high': 46.82,  # 价值区高点 (70%成交量区间上沿)
}
```

**原理说明**:
- **POC**: 大多数交易发生的价格，视为"公平价值"
- **Value Area**: 70%成交量集中的区间，是机构主要活动区域
- **价格 < VA Low**: 可能被低估，关注买入机会
- **价格 > VA High**: 可能被高估，关注卖出机会

### 3. 点数图测算 (Point & Figure)

```python
{
    'box_size': 0.45,          # 每格大小 (1% × LTP)
    'current_trend': 'X',      # X=上涨列, O=下跌列
    'current_column_boxes': 10,# 当前列格数
    'targets': {
        'bullish_neutral': 48.64,    # 中性看涨目标
        'bullish_aggressive': 50.67, # 激进看涨目标
        'congestion_width': 3,       # 盘整区宽度(列数)
    }
}
```

**原理说明 - 横向计数法**:
```
测算公式: 目标价 = 盘整区底部 + (盘整宽度 × Box × 反转格数)

示例:
  盘整区: 3列 × 7boxes高度 @ ¥44.59~¥47.74
  测幅: 3列 × ¥0.45 × 3格 = ¥4.05
  目标: ¥44.59 + ¥4.05 = ¥48.64 (+8.7%)
```

**为什么有效**: 盘整区的宽度反映了累积/派发的强度，宽度越大，突破后的力量越强。

### 4. 威科夫信号 (Wyckoff Signals)

```python
{
    'daily': {
        'spring_candidate': True,      # Spring候选 (假跌破后快速反弹)
        'upthrust_candidate': False,   # Upthrust候选 (假突破后快速回落)
        'volume_spike': False,         # 成交量激增
        'tr_width_pct': 19.46,         # TR宽度%
        'position_in_tr': 55.22,       # 在TR中的位置
    },
    'weekly': {
        'trend': 'downtrend',          # 周线趋势
        'position': 26.22,             # 周线在TR中的位置
    },
    'multi_timeframe': {
        'alignment': 'mixed',          # 多周期共振评估
        'confidence': 'medium',        # 置信度
    }
}
```

**原理说明**:

**Spring (弹簧)**:
```
定义: 价格短暂跌破TR低点，但快速反弹回区间内
特征:
  1. 跌破前低 (制造恐慌)
  2. 成交量放大 (散户割肉)
  3. 收盘回区间 (大户吸收)
意义: 供应耗尽，即将上涨
```

**Upthrust (向上假突破)**:
```
定义: 价格短暂突破TR高点，但快速回落至区间内
特征:
  1. 突破前高 (制造贪婪)
  2. 成交量放大 (散户追涨)
  3. 收盘回区间 (大户出货)
意义: 需求耗尽，即将下跌
```

**多周期共振**:
```
strong_accumulation: 周线<30% + 日线<40% = 强烈买入信号
strong_distribution: 周线>70% + 日线>60% = 强烈卖出信号
mixed: 周期之间矛盾 = 观望
```

### 5. 概率评估 (Probabilities)

| 指标 | 含义 | 计算逻辑 |
|-----|------|---------|
| Spring概率 | 未来5天出现Spring的可能性 | TR位置 + 历史模式 + 成交量 |
| 向上突破概率 | 未来10天突破TR高点的可能性 | 趋势方向 + 多周期共振 |
| Distribution概率 | 未来5天进入派发的可能性 | TR位置 > 70% + 成交量分布 |
| 趋势延续概率 | 当前趋势继续的可能性 | 均线排列 + 动量指标 |

**原理说明**: 基于历史统计模式，而非确定性预测。威科夫强调**概率思维**，而非绝对判断。

### 6. 行动假设 (Action Hypothesis)

威科夫交易计划模板:

```
假设1: [情景描述] (概率[X]%)
  触发: [具体条件，如"收盘突破¥46.82"]
  行动: [买入/卖出/观望]
  止损: ¥[价格] ([X]%风险)
  目标: ¥[价格] ([X]%收益)
  盈亏比: 1:[X]
```

**原理说明**: 威科夫强调**事前计划**，每笔交易前必须明确:
1. 入场条件 (什么情况下买入)
2. 止损位置 (什么情况下认错)
3. 目标位置 (什么情况下止盈)
4. 盈亏比 (收益/风险 > 3:1 才值得交易)

---

## 🎯 实战示例

### 示例1: 通富微电 (002156) - Spring交易

```bash
python akshare_fetcher.py analyze "002156" --pretty

# 关键信号:
# - TR位置: 55.2% (Phase C - Test of Supply)
# - Spring候选: True
# - 周线位置: 26.22% (周线底部)
# - 日线Spring概率: 50%

# 交易计划:
# 触发: 突破¥46.82 (VA High)
# 止损: ¥42.00 (-6.1%)
# 目标: ¥48.64 (P&F中性) / ¥50.67 (激进)
# 盈亏比: 1:1.5 (中性) / 1:2.2 (激进)
```

### 示例2: 云天化 (600096) - 大周期反转

```bash
python akshare_fetcher.py analyze "600096" --analysis-mode deep --pretty

# 深度分析关键发现:
# - 日线: 500根 (2年数据)
# - 周线: 200根 (4年数据)
# - 周线TR位置: 14.96% (大周期底部)
# - 日线TR位置: 15.51% (同步底部)
# - 多周期共振: strong_accumulation (高置信度)
# - P&F目标: ¥39.57 (+18.9%)

# 大周期结构:
# 2022-2023: Distribution (¥61→¥35)
# 2023-2024: Markdown (¥35→¥21)
# 2024-至今: Accumulation Phase A (¥21→¥33)

# 交易计划:
# 触发: 日线突破¥36.6 / 周线突破¥38
# 止损: ¥30.5 (-8.3%)
# 目标: ¥39.6 / ¥42 / ¥45 (分批止盈)
# 持有周期: 3-6个月 (大周期持仓)
```

### 示例3: CLI快速分析

```bash
# 标准分析 - 快速判断
$ python akshare_fetcher.py analyze "隆基"
# 输出 JSON：包含 trend / phase / key_levels / probabilities

# 深度分析 - 长线布局
$ python akshare_fetcher.py analyze "隆基" --analysis-mode deep --pretty
# 输出 JSON：compact 模式（默认）
```

---

## 📖 威科夫交易检查清单

### 买入前检查 (3-5分钟确认)

```
☐ 日线处于Phase A或Phase B (TR底部)
☐ 周线趋势不再下跌或处于低位
☐ 5分钟收盘>60% of range + above VWAP
☐ Spring候选出现或Volume Spike确认
☐ 盈亏比 > 3:1
☐ 明确止损位 (TR低点下方)
```

### 卖出前检查

```
☐ 日线处于Phase D或Phase C末端 (TR顶部)
☐ 周线位置 > 70%
☐ 5分钟收盘<40% of range + below VWAP
☐ Upthrust候选出现
☐ 成交量在高位放大 (派发迹象)
```

---

## 🔧 高级用法

### 自定义分析参数

```bash
# 标准 vs 深度模式对比
python akshare_fetcher.py analyze "600519" > /tmp/standard.json
python akshare_fetcher.py analyze "600519" --analysis-mode deep > /tmp/deep.json

# 用 jq 对比关键字段
jq '.key_levels.tr_position_pct, .point_figure.lookback_days' /tmp/standard.json
jq '.key_levels.tr_position_pct, .point_figure.lookback_days' /tmp/deep.json
```

### 批量分析

```bash
for stock in 茅台 宁德时代 比亚迪; do
  python akshare_fetcher.py analyze "$stock" | jq -c '{symbol,trend,phase,tr_pos:.key_levels.tr_position_pct,spring_prob:.probabilities.spring_next_5d}'
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
2. **进阶**: 学习Phase A/B/C/D/E的识别
3. **实战**: 结合成交量确认信号
4. **精通**: 多周期共振分析 + 资金管理

---

## Data Source

- **Sina Finance** - 日线/周线/分钟线数据

## License

MIT

---

**Star this repo if you find it helpful! ⭐**

For issues and feature requests, please use GitHub Issues.

# Wyckoff VPA Skill v0.2.1

威科夫量价分析 (Wyckoff Volume-Price Analysis) Skill for Chinese A-shares.

## Features

- **智能股票查询**: 支持名称/简称/代码模糊查询
- **高速数据获取**: ~1.3s 并行获取日线/周线/5分钟数据
- **三周期分析**: 周线(趋势) + 日线(阶段) + 5分钟(确认)
- **点数图测算**: Box=1%×LTP, 3格反转, 200日回看
- **AI驱动报告**: 一句话归纳 + 威科夫价位缩略图 + P&F目标测算

## Installation

### Using requirements.txt (Recommended)

```bash
pip install -r requirements.txt
```

### Manual Installation

```bash
pip install akshare>=1.10.0 pandas>=1.5.0 numpy>=1.21.0
```

## Quick Start

```python
from akshare_fetcher import quick_analysis_v2, resolve_stock_code

# Step 1: 查询股票代码
result = resolve_stock_code("通富微电")  # 名称查询
result = resolve_stock_code("茅台")      # 简称查询
result = resolve_stock_code("002840")    # 代码查询

# Step 2: 执行分析
analysis = quick_analysis_v2("002156")
print(analysis)
```

### 股票查询示例

```python
# 精确匹配
resolve_stock_code("通富微电")  # → {'code': '002156', 'name': '通富微电', 'success': True}
resolve_stock_code("茅台")      # → {'code': '600519', 'name': '贵州茅台', 'success': True}

# 模糊匹配 (需要用户确认)
resolve_stock_code("微电")  # → {'matches': [('002156', '通富微电'), ...], 'requires_clarification': True}
```

## Report Output

报告包含:
1. **一句话归纳** - 通俗概括当前状态
2. **威科夫价位缩略图** - TR区间 + Value Area + 关键价位
3. **点数图测算** - 中性/激进目标价
4. **多周期验证** - 周线/日线/5分钟共振分析
5. **概率评估** - Spring/突破/Distribution概率
6. **行动假设** - 具体入场/止损/目标位

## Data Source

- **Sina Finance** - 日线/周线/分钟线数据

## License

MIT

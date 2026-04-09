# Wyckoff VPA Skill

威科夫量价分析 (Wyckoff Volume-Price Analysis) Skill for Chinese A-shares.

## Features

- **高速数据获取**: ~1.3s 并行获取日线/周线/5分钟数据
- **三周期分析**: 周线(趋势) + 日线(阶段) + 5分钟(确认)
- **点数图测算**: Box=1%×LTP, 3格反转, 200日回看
- **AI驱动报告**: 一句话归纳 + 威科夫价位缩略图 + P&F目标测算

## Installation

```bash
pip install akshare
```

## Quick Start

```python
from akshare_fetcher import quick_analysis_v2

result = quick_analysis_v2("002156")  # 通富微电
print(result)
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

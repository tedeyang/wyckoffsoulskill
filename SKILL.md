---
name: wyckoff-vpa
description: Use when analyzing Chinese A-shares, judging a stock's structure or buyability, or explaining Wyckoff/VPA output with multi-timeframe context, intraday 5-minute confirmation, or plain-language trade interpretation.
---

# Wyckoff VPA

Use this skill for A-share stock analysis. Resolve the symbol first, then read evidence before conclusions.

## Trigger Phrases

- 分析股票 / 看走势 / 这票怎么样 / 能不能买
- 深度研究 / 长线 / 大周期
- 说人话 / 简单点 / 新手 / 看不懂

## Workflow

1. Resolve first:

```bash
python vpa.py resolve "<query>"
```

- `success=true` and `requires_clarification=false`: continue with the returned `code`.
- `requires_clarification=true`: show `matches`, ask the user to choose, and do not guess.
- `success=false`: repeat `message` and ask for a full name or 6-digit code.

2. Analyze:

```bash
python vpa.py analyze "<query>"
python vpa.py analyze "<query>" --analysis-mode deep
```

- Default to `standard`.
- Use `deep` only for 长线 / 深度研究 / 更长周期.
- Use `--full` only when compact output lacks enough evidence.

## Read In This Order

1. Snapshot: `key_levels.current`, `raw_market_facts.live_session`, `raw_market_facts.minute_last_day`, `structural_context.trading_range.current_position_pct`
2. Background: `structural_context.weekly_context`, `structural_context.higher_timeframe_context.monthly_context`, `structural_context.multi_timeframe_alignment`
3. Evidence: highest-score `event_candidates`, then `effort_result`, then `absorption_and_acceptance`
4. Summary: `point_and_figure_summary`, `llm_digest`

## Output Contract

### Professional Mode

- Lead with one concise conclusion.
- Then cover: current location, multi-timeframe background, dominant events, 5-minute confirmation, risk or invalidation.
- Evidence before recommendation.

### Plain-Language Mode

Trigger when the user says `说人话 / 简单点 / 新手 / 看不懂`.

- 200 Chinese characters max.
- Avoid jargon such as `Spring`, `UTAD`, `VWAP`, `TR`, `POC`.
- Must include: 能不能买, 止损, 目标, 风险.
- Only cite prices or levels that exist in the payload. If no reliable level exists, say so instead of inventing one.

## Guardrails

- Prefer 5-minute bars for execution confirmation. If minute data is missing or stale, state the downgrade and lower confidence.
- During live trading, `raw_market_facts.live_session` is the current price source. Do not mistake the prior close for the live price.
- Higher timeframe sets context; 5-minute data confirms execution, not the entire thesis.
- Use Chinese Wyckoff terms: `Spring`=`弹簧`, `Shakeout`=`震仓`, `SOS`=`强势征兆`, `UT`=`上冲`, `UTAD`=`上冲后派发`, `SOW`=`弱势征兆`.
- Do not rely on removed legacy fields such as `trend`, `phase`, `probabilities`, or `optional_legacy_outputs`.

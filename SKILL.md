---
name: wyckoff-vpa
description: Use when analyzing Chinese A-shares by stock name or code, judging whether a stock is buyable, comparing multi-timeframe structure, or explaining Wyckoff/VPA output in either professional or plain-language mode.
---

# Wyckoff VPA

Chinese A-share Wyckoff/VPA analysis with evidence-first JSON output.

Install source:

- Repo: `https://github.com/tedeyang/wyckoffsoulskill`
- Releases: `https://github.com/tedeyang/wyckoffsoulskill/releases`

## Quick Start

```bash
python vpa.py "贵州茅台"
python vpa.py "600519"
python vpa.py "中国中免" --deep
```

Rules:

- The CLI has a single entry. Do not call a separate `resolve` or `analyze` subcommand.
- Input can be stock name, alias, or 6-digit code.
- Use `--deep` only for 长线 / 深度研究 / 更长周期背景.

## What The CLI Does

1. Resolve the stock name or code.
2. If one stock is matched, run analysis directly.
3. If the query is ambiguous, return candidate stock names and codes in `matches` and tell the user to rerun with a more precise query.
4. If analysis succeeds, return compact JSON by default.

## Response Handling

### Exact Match

When `success=true`, read the returned evidence package and answer from it.

### Ambiguous Query

When `requires_clarification=true`:

- Show the top candidates from `matches`
- Keep both name and code
- Ask the user to rerun with a more precise stock name or 6-digit code
- Do not guess

### Failed Query

When `success=false` and no exact match exists:

- Repeat `message`
- Ask for a more accurate stock name or 6-digit code
- Do not fabricate symbol mappings

## Read In This Order

1. Snapshot
   - `key_levels.current`
   - `raw_market_facts.live_session`
   - `raw_market_facts.minute_last_day`
   - `structural_context.trading_range.current_position_pct`
2. Background
   - `structural_context.weekly_context`
   - `structural_context.higher_timeframe_context.monthly_context`
   - `structural_context.multi_timeframe_alignment`
3. Evidence
   - `event_candidates`
   - `effort_result`
   - `absorption_and_acceptance`
4. Summary
   - `point_and_figure_summary`
   - `llm_digest`

## Core Rules

1. Evidence before conclusion. Do not skip `event_candidates`, `effort_result`, or `absorption_and_acceptance`.
2. During live trading, prefer `raw_market_facts.live_session` over prior close.
3. Use 5-minute data for execution confirmation, not to override the higher-timeframe thesis.
4. If minute data is missing or stale, state the downgrade and lower confidence.
5. Do not rely on removed legacy fields such as `trend`, `phase`, `probabilities`, or `optional_legacy_outputs`.

## 5-Minute Confirmation

- Bullish confirmation: `close_position > 0.60` and `vs_vwap = above`
- Bearish confirmation: `close_position < 0.40` and `vs_vwap = below`
- Neutral: `0.40 ~ 0.60`

Also check:

- `gap_pct` and `gap_filled`
- `supply_bars / demand_bars`
- Whether intraday highs or lows were broken

## Output Contract

### Professional Mode

Default mode:

- Lead with one concise conclusion
- Then cover:
  - current location
  - multi-timeframe background
  - dominant events
  - 5-minute confirmation
  - risk or invalidation

### Plain-Language Mode

Trigger when the user says `说人话 / 简单点 / 新手 / 看不懂`.

- Use 200 Chinese characters or less
- Avoid jargon such as `Spring`, `UTAD`, `VWAP`, `TR`, `POC`
- Must include:
  - 能不能买
  - 止损
  - 目标
  - 风险
- Only cite prices or levels that exist in the payload. If no reliable level exists, say so instead of inventing one.

## Wyckoff Terms

Use Chinese labels in user-facing answers:

- `Spring` = `弹簧`
- `Shakeout` = `震仓`
- `SOS` = `强势征兆`
- `UT` = `上冲`
- `UTAD` = `上冲后派发`
- `SOW` = `弱势征兆`

## Install Or Remove

Examples:

```bash
python -m installer.install install --target codex
python -m installer.install install --target claudecode
python -m installer.install install --target all --adapters-root ./adapters-out

python -m installer.install uninstall --target codex
python -m installer.install uninstall --target all --adapters-root ./adapters-out
```

For agents, the main install path is to read the GitHub repo or release package, then run the installer locally.

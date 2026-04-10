"""
Evidence-first Wyckoff analysis engine.

This module keeps the data acquisition path intact while replacing the
middle analysis layer with a structured evidence package that is easier for
LLMs and downstream automation to audit.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


EVENT_CODES = [
    "PS",
    "PSY",
    "SC",
    "BC",
    "AR",
    "ST",
    "Spring",
    "Shakeout",
    "Test",
    "SOS",
    "LPS",
    "LPSY",
    "UT",
    "UTAD",
    "SOW",
]

EVENT_LABELS_ZH = {
    "PS": "初步支撑",
    "PSY": "初步供应",
    "SC": "卖出高潮",
    "BC": "买入高潮",
    "AR": "自动反弹",
    "ST": "二次测试",
    "Spring": "弹簧",
    "Shakeout": "震仓",
    "Test": "测试",
    "SOS": "强势征兆",
    "LPS": "最后支撑点",
    "LPSY": "最后供应点",
    "UT": "上冲",
    "UTAD": "上冲后派发",
    "SOW": "弱势征兆",
}

ALIGNMENT_LABELS_ZH = {
    "aligned": "同向",
    "partially_aligned": "部分同向",
    "mixed": "分歧",
}

BIAS_LABELS_ZH = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
}

POSITION_BUCKET_LABELS_ZH = {
    "low": "低位",
    "mid": "中位",
    "high": "高位",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round(value: Any, digits: int = 4) -> Any:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return round(number, digits)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    size = len(ordered)
    mid = size // 2
    if size % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bar_label(bar: Mapping[str, Any]) -> str:
    return str(bar.get("date") or bar.get("time") or "unknown")


def _bar_spread(bar: Mapping[str, Any]) -> float:
    return max(0.0, _to_float(bar.get("high")) - _to_float(bar.get("low")))


def _bar_body(bar: Mapping[str, Any]) -> float:
    return abs(_to_float(bar.get("close")) - _to_float(bar.get("open")))


def _bar_close_quality(bar: Mapping[str, Any]) -> float:
    spread = _bar_spread(bar)
    if spread <= 0:
        return 0.5
    return _clamp((_to_float(bar.get("close")) - _to_float(bar.get("low"))) / spread)


def _down_close_quality(bar: Mapping[str, Any]) -> float:
    return 1.0 - _bar_close_quality(bar)


def _volume_ratio(bar: Mapping[str, Any], avg_volume: float) -> float:
    if avg_volume <= 0:
        return 1.0
    return _to_float(bar.get("volume")) / avg_volume


def _price_zone(reference_low: float, reference_high: float) -> Dict[str, float]:
    return {
        "low": _round(reference_low, 2),
        "high": _round(reference_high, 2),
        "mid": _round((reference_low + reference_high) / 2.0, 2),
    }


def _to_bar_records(data: Any) -> List[Dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        raw_records = data
    elif hasattr(data, "to_dict"):
        try:
            raw_records = data.to_dict(orient="records")
        except TypeError:
            raw_records = data.to_dict("records")
    else:
        raw_records = list(data)

    records: List[Dict[str, Any]] = []
    for item in raw_records:
        if not isinstance(item, Mapping):
            continue
        record = dict(item)
        record["open"] = _to_float(record.get("open"))
        record["high"] = _to_float(record.get("high"))
        record["low"] = _to_float(record.get("low"))
        record["close"] = _to_float(record.get("close"))
        record["volume"] = _to_float(record.get("volume"))
        if "date" not in record and "time" in record:
            record["date"] = str(record.get("time"))[:10]
        records.append(record)
    return records


def _derive_key_levels(daily_bars: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not daily_bars:
        return {}
    closes = [_to_float(bar.get("close")) for bar in daily_bars]
    current = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else current
    recent_20 = list(daily_bars[-20:]) or list(daily_bars)
    highs = [_to_float(bar.get("high")) for bar in recent_20]
    lows = [_to_float(bar.get("low")) for bar in recent_20]
    tr_high = max(highs) if highs else current
    tr_low = min(lows) if lows else current
    tr_width = tr_high - tr_low
    tr_position = ((current - tr_low) / tr_width * 100.0) if tr_width > 0 else 50.0

    def rolling_mean(window: int) -> float:
        sample = closes[-window:] if len(closes) >= window else closes
        return _mean(sample)

    return {
        "current": _round(current, 2),
        "prev_close": _round(prev_close, 2),
        "change_pct": _round(((current - prev_close) / prev_close * 100.0) if prev_close else 0.0, 2),
        "tr_high_20d": _round(tr_high, 2),
        "tr_low_20d": _round(tr_low, 2),
        "tr_mid": _round((tr_high + tr_low) / 2.0, 2),
        "tr_position_pct": _round(tr_position, 1),
        "ma5": _round(rolling_mean(5), 2),
        "ma10": _round(rolling_mean(10), 2),
        "ma20": _round(rolling_mean(20), 2),
    }


def _extract_last_date(records: Sequence[Mapping[str, Any]]) -> Optional[str]:
    if not records:
        return None
    return _bar_label(records[-1])[:10]


def build_live_session_overlay(
    daily_bars: Sequence[Mapping[str, Any]],
    minute_bars: Sequence[Mapping[str, Any]],
    minute_analysis: Optional[Mapping[str, Any]],
    key_levels: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    daily_last_date = _extract_last_date(daily_bars)
    minute_last_date = None
    if minute_analysis and minute_analysis.get("date"):
        minute_last_date = str(minute_analysis.get("date"))[:10]
    elif minute_bars:
        minute_last_date = _extract_last_date(minute_bars)

    minute_last_close = None
    if minute_analysis and minute_analysis.get("day_close") is not None:
        minute_last_close = _to_float(minute_analysis.get("day_close"))
    elif minute_bars:
        minute_last_close = _to_float(minute_bars[-1].get("close"))

    prev_close = _to_float((key_levels or {}).get("prev_close"))
    session_high = _to_float((minute_analysis or {}).get("day_high"))
    session_low = _to_float((minute_analysis or {}).get("day_low"))
    is_live_session = bool(
        minute_last_date
        and daily_last_date
        and minute_last_date > daily_last_date
        and minute_last_close
    )

    return {
        "is_live_session": is_live_session,
        "source": "minute_last_day" if is_live_session else "daily_close",
        "daily_last_date": daily_last_date,
        "session_date": minute_last_date,
        "current_price": _round(minute_last_close, 2) if minute_last_close else None,
        "prev_close": _round(prev_close, 2) if prev_close else None,
        "change_pct": _round(((minute_last_close - prev_close) / prev_close * 100.0), 2) if is_live_session and prev_close else None,
        "session_high": _round(session_high, 2) if session_high else None,
        "session_low": _round(session_low, 2) if session_low else None,
        "stale_daily_snapshot": bool(is_live_session and daily_last_date != minute_last_date),
    }


def apply_live_session_overlay_to_key_levels(
    key_levels: Optional[Mapping[str, Any]],
    live_session: Mapping[str, Any],
) -> Dict[str, Any]:
    effective = dict(key_levels or {})
    if not live_session.get("is_live_session"):
        return effective

    current = _to_float(live_session.get("current_price"))
    prev_close = _to_float(live_session.get("prev_close"))
    if current <= 0:
        return effective

    tr_high = max(_to_float(effective.get("tr_high_20d")), _to_float(live_session.get("session_high")) or current)
    existing_low = _to_float(effective.get("tr_low_20d"))
    session_low = _to_float(live_session.get("session_low"))
    if existing_low > 0 and session_low > 0:
        tr_low = min(existing_low, session_low)
    else:
        tr_low = existing_low or session_low or current
    tr_width = tr_high - tr_low

    effective["current"] = _round(current, 2)
    effective["prev_close"] = _round(prev_close, 2) if prev_close else effective.get("prev_close")
    effective["change_pct"] = _round(((current - prev_close) / prev_close * 100.0), 2) if prev_close else effective.get("change_pct")
    effective["tr_high_20d"] = _round(tr_high, 2)
    effective["tr_low_20d"] = _round(tr_low, 2)
    effective["tr_mid"] = _round((tr_high + tr_low) / 2.0, 2)
    effective["tr_position_pct"] = _round(((current - tr_low) / tr_width * 100.0), 1) if tr_width > 0 else effective.get("tr_position_pct")
    return effective


def build_live_session_daily_bar(
    minute_analysis: Optional[Mapping[str, Any]],
    prev_close: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    if not minute_analysis or minute_analysis.get("error"):
        return None
    session_date = minute_analysis.get("date")
    day_close = _to_float(minute_analysis.get("day_close"))
    day_high = _to_float(minute_analysis.get("day_high"))
    day_low = _to_float(minute_analysis.get("day_low"))
    total_volume = _to_float(minute_analysis.get("total_volume"))
    if not session_date or day_close <= 0 or day_high <= 0 or day_low <= 0:
        return None
    open_price = _to_float(minute_analysis.get("day_open"))
    if open_price <= 0:
        open_price = prev_close if prev_close and prev_close > 0 else day_close
    return {
        "date": str(session_date)[:10],
        "open": _round(open_price, 4),
        "high": _round(day_high, 4),
        "low": _round(day_low, 4),
        "close": _round(day_close, 4),
        "volume": _round(total_volume, 4),
    }


def merge_live_session_into_daily_records(
    daily_bars: Sequence[Mapping[str, Any]],
    live_session: Mapping[str, Any],
    minute_analysis: Optional[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    records = [dict(bar) for bar in daily_bars]
    if not live_session.get("is_live_session"):
        return records
    prev_close = _to_float(live_session.get("prev_close"))
    live_bar = build_live_session_daily_bar(minute_analysis, prev_close=prev_close)
    if not live_bar:
        return records
    live_date = str(live_bar.get("date"))
    if records and _bar_label(records[-1])[:10] == live_date:
        records[-1] = live_bar
    else:
        records.append(live_bar)
    return records


def build_period_records_from_daily(
    daily_bars: Sequence[Mapping[str, Any]],
    period: str,
) -> List[Dict[str, Any]]:
    if period not in {"weekly", "monthly"}:
        raise ValueError(f"Unsupported period: {period}")

    records = _to_bar_records(daily_bars)
    if not records:
        return []

    buckets: Dict[str, List[Mapping[str, Any]]] = {}
    order: List[str] = []
    for bar in records:
        try:
            dt = datetime.strptime(_bar_label(bar)[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if period == "weekly":
            bucket_key = (dt + timedelta(days=(6 - dt.weekday()))).strftime("%Y-%m-%d")
        else:
            if dt.month == 12:
                month_end = datetime(dt.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(dt.year, dt.month + 1, 1) - timedelta(days=1)
            bucket_key = month_end.strftime("%Y-%m-%d")
        if bucket_key not in buckets:
            buckets[bucket_key] = []
            order.append(bucket_key)
        buckets[bucket_key].append(bar)

    aggregated: List[Dict[str, Any]] = []
    for bucket_key in order:
        bars = buckets[bucket_key]
        if not bars:
            continue
        aggregated.append(
            {
                "date": bucket_key,
                "open": _round(_to_float(bars[0].get("open")), 4),
                "high": _round(max(_to_float(bar.get("high")) for bar in bars), 4),
                "low": _round(min(_to_float(bar.get("low")) for bar in bars), 4),
                "close": _round(_to_float(bars[-1].get("close")), 4),
                "volume": _round(sum(_to_float(bar.get("volume")) for bar in bars), 4),
            }
        )
    return aggregated


@dataclass
class EventCandidateModel:
    event_code: str
    name: str
    timeframe: str
    candidate: bool
    detected: bool
    score: float
    price_zone: Dict[str, float]
    evidence: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.score = _round(_clamp(self.score), 4)
        self.candidate = bool(self.candidate)
        self.detected = bool(self.detected or self.score >= 0.75)


@dataclass
class SwingMetricModel:
    timeframe: str
    direction: str
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    amplitude: float
    amplitude_pct: float
    duration_bars: int
    total_volume: float
    average_spread: float
    close_quality: float
    efficiency: float
    volume_per_bar: float

    def __post_init__(self) -> None:
        self.start_price = _round(self.start_price, 4)
        self.end_price = _round(self.end_price, 4)
        self.amplitude = _round(self.amplitude, 4)
        self.amplitude_pct = _round(self.amplitude_pct, 2)
        self.total_volume = _round(self.total_volume, 2)
        self.average_spread = _round(self.average_spread, 4)
        self.close_quality = _round(_clamp(self.close_quality), 4)
        self.efficiency = _round(_clamp(self.efficiency), 4)
        self.volume_per_bar = _round(self.volume_per_bar, 2)


@dataclass
class WyckoffEvidencePackage:
    symbol: str
    analysis_mode: str
    schema_version: str
    key_levels: Dict[str, Any]
    raw_market_facts: Dict[str, Any]
    structural_context: Dict[str, Any]
    event_candidates: List[EventCandidateModel]
    swing_comparisons: List[SwingMetricModel]
    effort_result: Dict[str, Any]
    absorption_and_acceptance: Dict[str, Any]
    point_and_figure_summary: Dict[str, Any]
    inference_inputs: Dict[str, Any]
    llm_digest: Dict[str, Any]
    data_quality: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def serialize_analysis_package(payload: Any) -> Dict[str, Any]:
    if is_dataclass(payload):
        return asdict(payload)
    if isinstance(payload, dict):
        return payload
    raise TypeError("Unsupported payload type for JSON serialization")


def _event_score_map(
    event_candidates: Sequence[Mapping[str, Any]],
    timeframe: Optional[str] = None,
) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for event in event_candidates:
        if timeframe and event.get("timeframe") != timeframe:
            continue
        event_code = str(event.get("event_code") or "")
        if not event_code:
            continue
        scores[event_code] = _to_float(event.get("score"))
    return scores


def _make_event(
    event_code: str,
    timeframe: str,
    score: float,
    zone_low: float,
    zone_high: float,
    evidence: Optional[List[str]] = None,
) -> Dict[str, Any]:
    model = EventCandidateModel(
        event_code=event_code,
        name=EVENT_LABELS_ZH[event_code],
        timeframe=timeframe,
        candidate=score >= 0.35,
        detected=score >= 0.75,
        score=score,
        price_zone=_price_zone(zone_low, zone_high),
        evidence=evidence or [],
    )
    return asdict(model)


def _find_candidate_bars(
    bars: Sequence[Mapping[str, Any]],
    predicate,
) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for index, bar in enumerate(bars):
        if predicate(bar):
            enriched = dict(bar)
            enriched["_index"] = index
            matches.append(enriched)
    return matches


def detect_event_candidates(
    bars: Any,
    timeframe: str,
    range_low: Optional[float] = None,
    range_high: Optional[float] = None,
) -> List[Dict[str, Any]]:
    records = _to_bar_records(bars)
    if not records:
        return [_make_event(event_code, timeframe, 0.0, 0.0, 0.0) for event_code in EVENT_CODES]

    recent = records[-min(40, len(records)) :]
    highs = [_to_float(bar.get("high")) for bar in recent]
    lows = [_to_float(bar.get("low")) for bar in recent]
    closes = [_to_float(bar.get("close")) for bar in recent]
    range_low = min(lows) if range_low is None else float(range_low)
    range_high = max(highs) if range_high is None else float(range_high)
    width = max(range_high - range_low, 1e-9)
    avg_volume = _mean([_to_float(bar.get("volume")) for bar in recent]) or 1.0
    avg_spread = _mean([_bar_spread(bar) for bar in recent]) or 1e-9
    support_cap = range_low + width * 0.2
    resistance_floor = range_high - width * 0.2

    spring_candidates = _find_candidate_bars(
        recent,
        lambda bar: _to_float(bar.get("low")) < range_low
        and _to_float(bar.get("close")) >= range_low
        and _bar_close_quality(bar) >= 0.55,
    )
    ut_candidates = _find_candidate_bars(
        recent,
        lambda bar: _to_float(bar.get("high")) > range_high
        and _to_float(bar.get("close")) <= range_high
        and _bar_close_quality(bar) <= 0.45,
    )
    sell_climax_candidates = _find_candidate_bars(
        recent,
        lambda bar: _to_float(bar.get("low")) <= support_cap
        and _bar_spread(bar) >= avg_spread * 1.35
        and _volume_ratio(bar, avg_volume) >= 1.35,
    )
    buy_climax_candidates = _find_candidate_bars(
        recent,
        lambda bar: _to_float(bar.get("high")) >= resistance_floor
        and _bar_spread(bar) >= avg_spread * 1.35
        and _volume_ratio(bar, avg_volume) >= 1.35,
    )

    def best_bar(candidates: Sequence[Mapping[str, Any]], key_fn) -> Optional[Mapping[str, Any]]:
        if not candidates:
            return None
        return max(candidates, key=key_fn)

    spring_bar = best_bar(
        spring_candidates,
        lambda bar: _volume_ratio(bar, avg_volume) + _bar_close_quality(bar),
    )
    ut_bar = best_bar(
        ut_candidates,
        lambda bar: _volume_ratio(bar, avg_volume) + _down_close_quality(bar),
    )
    sc_bar = best_bar(
        sell_climax_candidates,
        lambda bar: _volume_ratio(bar, avg_volume) * _bar_spread(bar),
    )
    bc_bar = best_bar(
        buy_climax_candidates,
        lambda bar: _volume_ratio(bar, avg_volume) * _bar_spread(bar),
    )

    event_map: Dict[str, Dict[str, Any]] = {}

    if spring_bar:
        undercut_pct = max(0.0, (range_low - _to_float(spring_bar.get("low"))) / max(range_low, 1e-9))
        spring_score = (
            0.25
            + min(0.25, undercut_pct * 8.0)
            + 0.2
            + 0.15 * _bar_close_quality(spring_bar)
            + min(0.15, max(0.0, _volume_ratio(spring_bar, avg_volume) - 1.0) * 0.15)
        )
        spring_evidence = [
            f"{_bar_label(spring_bar)} 下破支撑 {_round(undercut_pct * 100.0, 2)}% 后重新收回区间",
            f"close_quality={_round(_bar_close_quality(spring_bar), 2)}，volume_ratio={_round(_volume_ratio(spring_bar, avg_volume), 2)}",
        ]
        event_map["Spring"] = _make_event("Spring", timeframe, spring_score, range_low, support_cap, spring_evidence)

        shakeout_score = spring_score - 0.1 + min(0.15, undercut_pct * 10.0)
        shakeout_evidence = list(spring_evidence)
        shakeout_evidence.append("下破深度更大，震仓特征更明显")
        event_map["Shakeout"] = _make_event("Shakeout", timeframe, shakeout_score, range_low, support_cap, shakeout_evidence)
    else:
        event_map["Spring"] = _make_event("Spring", timeframe, 0.0, range_low, support_cap)
        event_map["Shakeout"] = _make_event("Shakeout", timeframe, 0.0, range_low, support_cap)

    if ut_bar:
        overshoot_pct = max(0.0, (_to_float(ut_bar.get("high")) - range_high) / max(range_high, 1e-9))
        ut_score = (
            0.25
            + min(0.25, overshoot_pct * 8.0)
            + 0.15 * _down_close_quality(ut_bar)
            + min(0.2, max(0.0, _volume_ratio(ut_bar, avg_volume) - 1.0) * 0.2)
            + 0.15
        )
        ut_evidence = [
            f"{_bar_label(ut_bar)} 上破区间 {_round(overshoot_pct * 100.0, 2)}% 后回落失败",
            f"rejection_close_quality={_round(_down_close_quality(ut_bar), 2)}，volume_ratio={_round(_volume_ratio(ut_bar, avg_volume), 2)}",
        ]
        event_map["UT"] = _make_event("UT", timeframe, ut_score, resistance_floor, range_high, ut_evidence)

        utad_score = ut_score - 0.05 + min(0.15, overshoot_pct * 12.0)
        utad_evidence = list(ut_evidence)
        utad_evidence.append("阻力上方未形成接受，UTAD 风险上升")
        event_map["UTAD"] = _make_event("UTAD", timeframe, utad_score, resistance_floor, range_high, utad_evidence)
    else:
        event_map["UT"] = _make_event("UT", timeframe, 0.0, resistance_floor, range_high)
        event_map["UTAD"] = _make_event("UTAD", timeframe, 0.0, resistance_floor, range_high)

    if sc_bar:
        sc_score = (
            0.2
            + min(0.3, (_bar_spread(sc_bar) / avg_spread - 1.0) * 0.2)
            + min(0.25, (_volume_ratio(sc_bar, avg_volume) - 1.0) * 0.18)
            + 0.15 * _down_close_quality(sc_bar)
        )
        sc_evidence = [
            f"{_bar_label(sc_bar)} 在支撑附近出现 {_round(_bar_spread(sc_bar) / avg_spread, 2)} 倍平均波幅",
            f"volume_ratio={_round(_volume_ratio(sc_bar, avg_volume), 2)}，存在供给高潮迹象",
        ]
        event_map["SC"] = _make_event("SC", timeframe, sc_score, range_low, support_cap, sc_evidence)
    else:
        event_map["SC"] = _make_event("SC", timeframe, 0.0, range_low, support_cap)

    if bc_bar:
        bc_score = (
            0.2
            + min(0.3, (_bar_spread(bc_bar) / avg_spread - 1.0) * 0.2)
            + min(0.25, (_volume_ratio(bc_bar, avg_volume) - 1.0) * 0.18)
            + 0.15 * _bar_close_quality(bc_bar)
        )
        bc_evidence = [
            f"{_bar_label(bc_bar)} 在阻力附近出现 {_round(_bar_spread(bc_bar) / avg_spread, 2)} 倍平均波幅",
            f"volume_ratio={_round(_volume_ratio(bc_bar, avg_volume), 2)}，存在需求高潮迹象",
        ]
        event_map["BC"] = _make_event("BC", timeframe, bc_score, resistance_floor, range_high, bc_evidence)
    else:
        event_map["BC"] = _make_event("BC", timeframe, 0.0, resistance_floor, range_high)

    def bar_after(index: Optional[int], window: int = 3) -> List[Mapping[str, Any]]:
        if index is None:
            return []
        start = index + 1
        end = min(len(recent), index + 1 + window)
        return list(recent[start:end])

    sc_index = int(sc_bar["_index"]) if sc_bar else None
    bc_index = int(bc_bar["_index"]) if bc_bar else None
    spring_index = int(spring_bar["_index"]) if spring_bar else None
    ut_index = int(ut_bar["_index"]) if ut_bar else None

    if sc_bar and bar_after(sc_index):
        ar_bar = max(bar_after(sc_index), key=lambda bar: _to_float(bar.get("close")))
        rebound_pct = (_to_float(ar_bar.get("close")) - _to_float(sc_bar.get("low"))) / width
        ar_score = 0.2 + min(0.35, max(0.0, rebound_pct) * 0.6) + 0.15 * _bar_close_quality(ar_bar)
        ar_evidence = [
            f"{_bar_label(ar_bar)} 在卖出高潮后反弹了活跃区间的 {_round(rebound_pct * 100.0, 2)}%",
            f"close_quality={_round(_bar_close_quality(ar_bar), 2)}",
        ]
        event_map["AR"] = _make_event("AR", timeframe, ar_score, range_low, range_low + width * 0.35, ar_evidence)
    elif bc_bar and bar_after(bc_index):
        ar_bar = min(bar_after(bc_index), key=lambda bar: _to_float(bar.get("close")))
        reaction_pct = (_to_float(bc_bar.get("high")) - _to_float(ar_bar.get("close"))) / width
        ar_score = 0.2 + min(0.35, max(0.0, reaction_pct) * 0.6) + 0.15 * _down_close_quality(ar_bar)
        ar_evidence = [
            f"{_bar_label(ar_bar)} 在买入高潮后回落了活跃区间的 {_round(reaction_pct * 100.0, 2)}%",
            f"rejection_close_quality={_round(_down_close_quality(ar_bar), 2)}",
        ]
        event_map["AR"] = _make_event("AR", timeframe, ar_score, range_high - width * 0.35, range_high, ar_evidence)
    else:
        event_map["AR"] = _make_event("AR", timeframe, 0.0, range_low, range_high)

    if sc_bar:
        st_candidates = _find_candidate_bars(
            recent[sc_index + 1 :],
            lambda bar: abs(_to_float(bar.get("low")) - _to_float(sc_bar.get("low"))) <= width * 0.04
            and _volume_ratio(bar, avg_volume) <= _volume_ratio(sc_bar, avg_volume),
        )
        st_bar = st_candidates[-1] if st_candidates else None
        if st_bar:
            st_score = 0.25 + 0.2 * _bar_close_quality(st_bar) + 0.2 * (1.0 - _volume_ratio(st_bar, avg_volume))
            st_evidence = [
                f"{_bar_label(st_bar)} 以更低成交量回测卖出高潮低点",
                f"close_quality={_round(_bar_close_quality(st_bar), 2)}，volume_ratio={_round(_volume_ratio(st_bar, avg_volume), 2)}",
            ]
            event_map["ST"] = _make_event("ST", timeframe, st_score, range_low, support_cap, st_evidence)
        else:
            event_map["ST"] = _make_event("ST", timeframe, 0.0, range_low, support_cap)
    elif bc_bar:
        st_candidates = _find_candidate_bars(
            recent[bc_index + 1 :],
            lambda bar: abs(_to_float(bar.get("high")) - _to_float(bc_bar.get("high"))) <= width * 0.04
            and _volume_ratio(bar, avg_volume) <= _volume_ratio(bc_bar, avg_volume),
        )
        st_bar = st_candidates[-1] if st_candidates else None
        if st_bar:
            st_score = 0.25 + 0.2 * _down_close_quality(st_bar) + 0.2 * (1.0 - _volume_ratio(st_bar, avg_volume))
            st_evidence = [
                f"{_bar_label(st_bar)} 以更低成交量回测买入高潮高点",
                f"rejection_close_quality={_round(_down_close_quality(st_bar), 2)}，volume_ratio={_round(_volume_ratio(st_bar, avg_volume), 2)}",
            ]
            event_map["ST"] = _make_event("ST", timeframe, st_score, resistance_floor, range_high, st_evidence)
        else:
            event_map["ST"] = _make_event("ST", timeframe, 0.0, resistance_floor, range_high)
    else:
        event_map["ST"] = _make_event("ST", timeframe, 0.0, range_low, range_high)

    test_candidates = _find_candidate_bars(
        recent[-10:],
        lambda bar: abs(_to_float(bar.get("low")) - range_low) <= width * 0.03
        and _volume_ratio(bar, avg_volume) <= 0.9
        and _bar_close_quality(bar) >= 0.55,
    )
    if test_candidates:
        test_bar = max(test_candidates, key=lambda bar: _bar_close_quality(bar) - _volume_ratio(bar, avg_volume))
        test_score = 0.25 + 0.25 * _bar_close_quality(test_bar) + 0.25 * (1.0 - _volume_ratio(test_bar, avg_volume))
        test_evidence = [
            f"{_bar_label(test_bar)} 缩量回踩支撑",
            f"close_quality={_round(_bar_close_quality(test_bar), 2)}，volume_ratio={_round(_volume_ratio(test_bar, avg_volume), 2)}",
        ]
        if spring_index is not None and int(test_bar["_index"]) > spring_index:
            test_score += 0.1
            test_evidence.append("出现在弹簧/震仓之后")
        event_map["Test"] = _make_event("Test", timeframe, test_score, range_low, support_cap, test_evidence)
    else:
        event_map["Test"] = _make_event("Test", timeframe, 0.0, range_low, support_cap)

    sos_candidates = _find_candidate_bars(
        recent[-10:],
        lambda bar: _to_float(bar.get("close")) >= resistance_floor
        and _bar_close_quality(bar) >= 0.7
        and _bar_spread(bar) >= avg_spread * 1.1
        and _volume_ratio(bar, avg_volume) >= 1.0,
    )
    if sos_candidates:
        sos_bar = max(sos_candidates, key=lambda bar: _bar_close_quality(bar) + _volume_ratio(bar, avg_volume))
        breakout_pct = max(0.0, (_to_float(sos_bar.get("close")) - resistance_floor) / width)
        sos_score = 0.25 + 0.2 * _bar_close_quality(sos_bar) + 0.15 * min(1.0, breakout_pct * 3.0) + 0.15 * min(1.0, _volume_ratio(sos_bar, avg_volume) - 0.8)
        sos_evidence = [
            f"{_bar_label(sos_bar)} 收于区间上沿，spread_ratio={_round(_bar_spread(sos_bar) / avg_spread, 2)}",
            f"volume_ratio={_round(_volume_ratio(sos_bar, avg_volume), 2)}，突破推进={_round(breakout_pct * 100.0, 2)}%",
        ]
        event_map["SOS"] = _make_event("SOS", timeframe, sos_score, resistance_floor, range_high, sos_evidence)
    else:
        sos_bar = None
        event_map["SOS"] = _make_event("SOS", timeframe, 0.0, resistance_floor, range_high)

    sow_candidates = _find_candidate_bars(
        recent[-10:],
        lambda bar: _to_float(bar.get("close")) <= support_cap
        and _down_close_quality(bar) >= 0.7
        and _bar_spread(bar) >= avg_spread * 1.1
        and _volume_ratio(bar, avg_volume) >= 1.0,
    )
    if sow_candidates:
        sow_bar = max(sow_candidates, key=lambda bar: _down_close_quality(bar) + _volume_ratio(bar, avg_volume))
        breakdown_pct = max(0.0, (support_cap - _to_float(sow_bar.get("close"))) / width)
        sow_score = 0.25 + 0.2 * _down_close_quality(sow_bar) + 0.15 * min(1.0, breakdown_pct * 3.0) + 0.15 * min(1.0, _volume_ratio(sow_bar, avg_volume) - 0.8)
        sow_evidence = [
            f"{_bar_label(sow_bar)} 收于区间下沿，spread_ratio={_round(_bar_spread(sow_bar) / avg_spread, 2)}",
            f"volume_ratio={_round(_volume_ratio(sow_bar, avg_volume), 2)}，跌破推进={_round(breakdown_pct * 100.0, 2)}%",
        ]
        event_map["SOW"] = _make_event("SOW", timeframe, sow_score, range_low, support_cap, sow_evidence)
    else:
        sow_bar = None
        event_map["SOW"] = _make_event("SOW", timeframe, 0.0, range_low, support_cap)

    if sos_bar:
        sos_index = int(sos_bar["_index"])
        lps_candidates = _find_candidate_bars(
            recent[sos_index + 1 :],
            lambda bar: _to_float(bar.get("low")) >= range_low + width * 0.35
            and _volume_ratio(bar, avg_volume) <= 0.95,
        )
        lps_bar = lps_candidates[-1] if lps_candidates else None
        if lps_bar:
            lps_score = 0.25 + 0.2 * _bar_close_quality(lps_bar) + 0.2 * (1.0 - _volume_ratio(lps_bar, avg_volume))
            lps_evidence = [
                f"{_bar_label(lps_bar)} 在强势征兆后缩量回踩",
                f"close_quality={_round(_bar_close_quality(lps_bar), 2)}，volume_ratio={_round(_volume_ratio(lps_bar, avg_volume), 2)}",
            ]
            event_map["LPS"] = _make_event("LPS", timeframe, lps_score, range_low + width * 0.3, resistance_floor, lps_evidence)
        else:
            event_map["LPS"] = _make_event("LPS", timeframe, 0.0, range_low + width * 0.3, resistance_floor)
    else:
        event_map["LPS"] = _make_event("LPS", timeframe, 0.0, range_low + width * 0.3, resistance_floor)

    if sow_bar:
        sow_index = int(sow_bar["_index"])
        lpsy_candidates = _find_candidate_bars(
            recent[sow_index + 1 :],
            lambda bar: _to_float(bar.get("high")) <= range_high - width * 0.35
            and _volume_ratio(bar, avg_volume) <= 0.95,
        )
        lpsy_bar = lpsy_candidates[-1] if lpsy_candidates else None
        if lpsy_bar:
            lpsy_score = 0.25 + 0.2 * _down_close_quality(lpsy_bar) + 0.2 * (1.0 - _volume_ratio(lpsy_bar, avg_volume))
            lpsy_evidence = [
                f"{_bar_label(lpsy_bar)} 在弱势征兆后弱反弹且成交量收缩",
                f"rejection_close_quality={_round(_down_close_quality(lpsy_bar), 2)}，volume_ratio={_round(_volume_ratio(lpsy_bar, avg_volume), 2)}",
            ]
            event_map["LPSY"] = _make_event("LPSY", timeframe, lpsy_score, support_cap, range_high - width * 0.3, lpsy_evidence)
        else:
            event_map["LPSY"] = _make_event("LPSY", timeframe, 0.0, support_cap, range_high - width * 0.3)
    else:
        event_map["LPSY"] = _make_event("LPSY", timeframe, 0.0, support_cap, range_high - width * 0.3)

    if sc_bar:
        window = recent[max(0, sc_index - 3) : sc_index]
        ps_bar = best_bar(
            _find_candidate_bars(
                window,
                lambda bar: _to_float(bar.get("low")) <= support_cap and _volume_ratio(bar, avg_volume) >= 1.05,
            ),
            lambda bar: _volume_ratio(bar, avg_volume),
        )
        if ps_bar:
            ps_score = 0.2 + 0.15 * min(1.0, _volume_ratio(ps_bar, avg_volume) - 0.8) + 0.15 * _bar_close_quality(ps_bar)
            ps_evidence = [
                f"{_bar_label(ps_bar)} 在卖出高潮前先出现初步支撑",
                f"volume_ratio={_round(_volume_ratio(ps_bar, avg_volume), 2)}，close_quality={_round(_bar_close_quality(ps_bar), 2)}",
            ]
            event_map["PS"] = _make_event("PS", timeframe, ps_score, range_low, support_cap, ps_evidence)
        else:
            event_map["PS"] = _make_event("PS", timeframe, 0.0, range_low, support_cap)
    else:
        event_map["PS"] = _make_event("PS", timeframe, 0.0, range_low, support_cap)

    if bc_bar:
        window = recent[max(0, bc_index - 3) : bc_index]
        psy_bar = best_bar(
            _find_candidate_bars(
                window,
                lambda bar: _to_float(bar.get("high")) >= resistance_floor and _volume_ratio(bar, avg_volume) >= 1.05,
            ),
            lambda bar: _volume_ratio(bar, avg_volume),
        )
        if psy_bar:
            psy_score = 0.2 + 0.15 * min(1.0, _volume_ratio(psy_bar, avg_volume) - 0.8) + 0.15 * _down_close_quality(psy_bar)
            psy_evidence = [
                f"{_bar_label(psy_bar)} 在买入高潮前先出现初步供应",
                f"volume_ratio={_round(_volume_ratio(psy_bar, avg_volume), 2)}，rejection_close_quality={_round(_down_close_quality(psy_bar), 2)}",
            ]
            event_map["PSY"] = _make_event("PSY", timeframe, psy_score, resistance_floor, range_high, psy_evidence)
        else:
            event_map["PSY"] = _make_event("PSY", timeframe, 0.0, resistance_floor, range_high)
    else:
        event_map["PSY"] = _make_event("PSY", timeframe, 0.0, resistance_floor, range_high)

    return [event_map[event_code] for event_code in EVENT_CODES]


def compute_swing_metrics(bars: Any, timeframe: str = "daily") -> List[Dict[str, Any]]:
    records = _to_bar_records(bars)
    if len(records) < 3:
        return []

    closes = [_to_float(bar.get("close")) for bar in records]
    direction_changes: List[int] = [0]
    previous_sign = 0
    for index in range(1, len(closes)):
        delta = closes[index] - closes[index - 1]
        sign = 1 if delta > 0 else -1 if delta < 0 else previous_sign
        if previous_sign != 0 and sign != previous_sign:
            direction_changes.append(index - 1)
        previous_sign = sign
    direction_changes.append(len(records) - 1)

    pivots: List[int] = []
    for pivot in direction_changes:
        if not pivots or pivot != pivots[-1]:
            pivots.append(pivot)

    swings: List[Dict[str, Any]] = []
    for start_index, end_index in zip(pivots, pivots[1:]):
        if end_index <= start_index:
            continue
        segment = records[start_index : end_index + 1]
        start_close = _to_float(segment[0].get("close"))
        end_close = _to_float(segment[-1].get("close"))
        path = sum(
            abs(_to_float(segment[i].get("close")) - _to_float(segment[i - 1].get("close")))
            for i in range(1, len(segment))
        )
        amplitude = end_close - start_close
        efficiency = abs(amplitude) / path if path > 0 else 0.0
        spreads = [_bar_spread(bar) for bar in segment]
        total_volume = sum(_to_float(bar.get("volume")) for bar in segment)
        model = SwingMetricModel(
            timeframe=timeframe,
            direction="up_swing" if amplitude >= 0 else "down_swing",
            start_date=_bar_label(segment[0]),
            end_date=_bar_label(segment[-1]),
            start_price=start_close,
            end_price=end_close,
            amplitude=abs(amplitude),
            amplitude_pct=(abs(amplitude) / start_close * 100.0) if start_close else 0.0,
            duration_bars=len(segment) - 1,
            total_volume=total_volume,
            average_spread=_mean(spreads),
            close_quality=_bar_close_quality(segment[-1]) if amplitude >= 0 else _down_close_quality(segment[-1]),
            efficiency=efficiency,
            volume_per_bar=total_volume / max(1, len(segment)),
        )
        swings.append(asdict(model))

    return swings[-6:]


def compute_effort_result_metrics(
    bars: Any,
    breakout_level: Optional[float] = None,
    breakdown_level: Optional[float] = None,
) -> Dict[str, Any]:
    records = _to_bar_records(bars)
    if not records:
        return {
            "spread_volume_ratio": 0.0,
            "close_quality_score": 0.0,
            "effort_result_divergence": 0.0,
            "breakout_efficiency": 0.0,
            "reversal_efficiency": 0.0,
            "high_volume_no_progress": False,
            "low_volume_pullback": False,
        }

    recent = records[-min(8, len(records)) :]
    avg_volume = _mean([_to_float(bar.get("volume")) for bar in recent[:-1]]) or _mean([_to_float(bar.get("volume")) for bar in recent]) or 1.0
    avg_spread = _mean([_bar_spread(bar) for bar in recent[:-1]]) or _mean([_bar_spread(bar) for bar in recent]) or 1e-9
    last_bar = recent[-1]
    last_volume_ratio = _volume_ratio(last_bar, avg_volume)
    last_spread_ratio = _bar_spread(last_bar) / avg_spread if avg_spread > 0 else 0.0
    spread_volume_ratio = last_spread_ratio / max(last_volume_ratio, 1e-9)
    close_quality_score = _bar_close_quality(last_bar)

    high_volume_bar = max(recent, key=lambda bar: _to_float(bar.get("volume")))
    high_volume_progress = _bar_body(high_volume_bar)
    result_ratio = max(
        high_volume_progress / max(avg_spread, 1e-9),
        _bar_spread(high_volume_bar) / max(avg_spread, 1e-9) * _bar_close_quality(high_volume_bar),
    )
    effort_result_divergence = _volume_ratio(high_volume_bar, avg_volume) - result_ratio

    breakout_efficiency = 0.0
    if breakout_level is not None:
        breakout_bars = [bar for bar in recent[-3:] if _to_float(bar.get("close")) > breakout_level]
        if breakout_bars:
            breakout_efficiency = _clamp(
                0.35
                + 0.3 * _mean([_bar_close_quality(bar) for bar in breakout_bars])
                + 0.25 * _mean(
                    [
                        (_to_float(bar.get("close")) - float(breakout_level)) / max(_bar_spread(bar), 1e-9)
                        for bar in breakout_bars
                    ]
                )
            )

    reversal_efficiency = 0.0
    if len(recent) >= 4:
        prior_leg = _to_float(recent[-2].get("close")) - _to_float(recent[-4].get("close"))
        current_leg = _to_float(recent[-1].get("close")) - _to_float(recent[-2].get("close"))
        if prior_leg != 0:
            reversal_efficiency = _clamp(abs(current_leg) / abs(prior_leg))

    high_volume_no_progress = (
        _volume_ratio(high_volume_bar, avg_volume) >= 1.35
        and high_volume_progress <= avg_spread * 0.35
    )

    low_volume_pullback = False
    if len(recent) >= 2:
        previous_bar = recent[-2]
        low_volume_pullback = (
            _to_float(last_bar.get("close")) < _to_float(previous_bar.get("close"))
            and _volume_ratio(last_bar, avg_volume) <= 0.9
        )

    if breakdown_level is not None and len(recent) >= 2 and _to_float(last_bar.get("close")) < float(breakdown_level):
        reversal_efficiency = max(reversal_efficiency, _clamp(_down_close_quality(last_bar)))

    return {
        "spread_volume_ratio": _round(spread_volume_ratio, 4),
        "close_quality_score": _round(close_quality_score, 4),
        "effort_result_divergence": _round(effort_result_divergence, 4),
        "breakout_efficiency": _round(breakout_efficiency, 4),
        "reversal_efficiency": _round(reversal_efficiency, 4),
        "high_volume_no_progress": bool(high_volume_no_progress),
        "low_volume_pullback": bool(low_volume_pullback),
    }


def compute_absorption_scores(
    bars: Any,
    range_low: float,
    range_high: float,
) -> Dict[str, Any]:
    records = _to_bar_records(bars)
    if not records:
        return {
            "supply_absorption_score": 0.0,
            "demand_absorption_score": 0.0,
            "breakout_acceptance_score": 0.0,
            "breakout_rejection_score": 0.0,
            "breakdown_acceptance_score": 0.0,
            "breakdown_rejection_score": 0.0,
            "follow_through_failure": False,
            "test_quality": 0.0,
        }

    recent = records[-min(10, len(records)) :]
    width = max(range_high - range_low, 1e-9)
    avg_volume = _mean([_to_float(bar.get("volume")) for bar in recent]) or 1.0

    support_touches = [
        bar
        for bar in recent
        if _to_float(bar.get("low")) <= range_low + width * 0.05
    ]
    resistance_touches = [
        bar
        for bar in recent
        if _to_float(bar.get("high")) >= range_high - width * 0.05
    ]
    closes_above_breakout = [bar for bar in recent if _to_float(bar.get("close")) > range_high]
    closes_below_breakdown = [bar for bar in recent if _to_float(bar.get("close")) < range_low]

    supply_absorption_score = 0.0
    if resistance_touches:
        supply_absorption_score = _clamp(
            0.2
            + 0.2 * (len(resistance_touches) / max(1, len(recent)))
            + 0.25 * _mean([_bar_close_quality(bar) for bar in resistance_touches])
            + 0.15 * _mean([min(1.0, _volume_ratio(bar, avg_volume)) for bar in resistance_touches])
        )

    demand_absorption_score = 0.0
    if support_touches:
        demand_absorption_score = _clamp(
            0.2
            + 0.2 * (len(support_touches) / max(1, len(recent)))
            + 0.25 * _mean([_bar_close_quality(bar) for bar in support_touches])
            + 0.15 * _mean([min(1.0, _volume_ratio(bar, avg_volume)) for bar in support_touches])
        )

    breakout_acceptance_score = 0.0
    if closes_above_breakout:
        breakout_acceptance_score = _clamp(
            0.4
            + 0.25 * _mean([_bar_close_quality(bar) for bar in closes_above_breakout])
            + 0.2 * (len(closes_above_breakout) / max(1, len(recent)))
        )

    breakout_rejection_events = [
        bar
        for bar in recent
        if _to_float(bar.get("high")) > range_high and _to_float(bar.get("close")) <= range_high
    ]
    breakout_rejection_score = 0.0
    if breakout_rejection_events:
        breakout_rejection_score = _clamp(
            0.2
            + 0.25 * _mean([_down_close_quality(bar) for bar in breakout_rejection_events])
            + 0.2 * (len(breakout_rejection_events) / max(1, len(recent)))
        )
    if closes_above_breakout and _to_float(recent[-1].get("close")) < range_high:
        breakout_rejection_score = max(breakout_rejection_score, 0.35)

    breakdown_acceptance_score = 0.0
    if closes_below_breakdown:
        breakdown_acceptance_score = _clamp(
            0.4
            + 0.25 * _mean([_down_close_quality(bar) for bar in closes_below_breakdown])
            + 0.2 * (len(closes_below_breakdown) / max(1, len(recent)))
        )

    breakdown_rejection_events = [
        bar
        for bar in recent
        if _to_float(bar.get("low")) < range_low and _to_float(bar.get("close")) >= range_low
    ]
    breakdown_rejection_score = 0.0
    if breakdown_rejection_events:
        breakdown_rejection_score = _clamp(
            0.2
            + 0.25 * _mean([_bar_close_quality(bar) for bar in breakdown_rejection_events])
            + 0.2 * (len(breakdown_rejection_events) / max(1, len(recent)))
        )
    if closes_below_breakdown and _to_float(recent[-1].get("close")) > range_low:
        breakdown_rejection_score = max(breakdown_rejection_score, 0.35)

    support_tests = [
        bar
        for bar in support_touches
        if _volume_ratio(bar, avg_volume) <= 0.95 and _bar_close_quality(bar) >= 0.55
    ]
    resistance_tests = [
        bar
        for bar in resistance_touches
        if _volume_ratio(bar, avg_volume) <= 0.95 and _down_close_quality(bar) >= 0.55
    ]
    test_quality = 0.0
    if support_tests or resistance_tests:
        support_quality = _mean(
            [(1.0 - _volume_ratio(bar, avg_volume)) + _bar_close_quality(bar) for bar in support_tests]
        )
        resistance_quality = _mean(
            [(1.0 - _volume_ratio(bar, avg_volume)) + _down_close_quality(bar) for bar in resistance_tests]
        )
        test_quality = _clamp(max(support_quality, resistance_quality) / 2.0)

    follow_through_failure = bool(
        (breakout_acceptance_score >= 0.45 and breakout_rejection_score >= 0.25)
        or (breakdown_acceptance_score >= 0.45 and breakdown_rejection_score >= 0.25)
    )

    return {
        "supply_absorption_score": _round(supply_absorption_score, 4),
        "demand_absorption_score": _round(demand_absorption_score, 4),
        "breakout_acceptance_score": _round(breakout_acceptance_score, 4),
        "breakout_rejection_score": _round(breakout_rejection_score, 4),
        "breakdown_acceptance_score": _round(breakdown_acceptance_score, 4),
        "breakdown_rejection_score": _round(breakdown_rejection_score, 4),
        "follow_through_failure": follow_through_failure,
        "test_quality": _round(test_quality, 4),
    }


def summarize_point_figure(point_figure: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not point_figure or not isinstance(point_figure, Mapping):
        return {
            "current_column_summary": {},
            "recent_reversal_summary": [],
            "bullish_count": 0,
            "bearish_count": 0,
            "congestion_width": 0,
            "measured_move": 0.0,
            "breakout_hints": [],
            "risk_hints": [],
            "catapult_hint": False,
            "failed_breakout_hint": False,
            "sign_of_weakness_risk_hint": False,
        }

    columns = list(point_figure.get("columns") or [])
    current_column = columns[-1] if columns else {}
    recent_columns = columns[-3:] if len(columns) >= 3 else columns
    bullish_count = sum(1 for col in columns if col.get("type") == "X")
    bearish_count = sum(1 for col in columns if col.get("type") == "O")
    targets = dict(point_figure.get("targets") or {})

    breakout_hints: List[str] = []
    risk_hints: List[str] = []
    catapult_hint = False
    failed_breakout_hint = False
    sign_of_weakness_risk_hint = False

    if len(columns) >= 2:
        previous = columns[-2]
        if current_column.get("type") == "X" and _to_float(current_column.get("end_price")) > _to_float(previous.get("end_price")):
            breakout_hints.append("当前 X 列已经上破前一列高点。")
        if current_column.get("type") == "O" and _to_float(current_column.get("end_price")) < _to_float(previous.get("end_price")):
            risk_hints.append("当前 O 列已经跌破前一列低点。")

    if len(columns) >= 3:
        c1, c2, c3 = columns[-3], columns[-2], columns[-1]
        if c1.get("type") == "X" and c2.get("type") == "O" and c3.get("type") == "X":
            if _to_float(c3.get("end_price")) > _to_float(c1.get("end_price")) and _to_float(c2.get("end_price")) >= _to_float(c1.get("start_price")):
                catapult_hint = True
                breakout_hints.append("X-O-X 序列接近看涨弹射形态。")
        if c1.get("type") == "X" and c2.get("type") == "O" and c3.get("type") == "O":
            failed_breakout_hint = True
            risk_hints.append("最近的反转序列更像一次失败的向上突破。")
        if c1.get("type") == "O" and c2.get("type") == "X" and c3.get("type") == "O":
            sign_of_weakness_risk_hint = True
            risk_hints.append("O-X-O 序列提升弱势征兆风险。")

    if targets.get("direction") == "bullish":
        breakout_hints.append("测幅目标指向向上扩展。")
    if targets.get("direction") == "bearish":
        risk_hints.append("测幅目标指向向下扩展。")

    return {
        "current_column_summary": {
            "type": current_column.get("type"),
            "boxes": current_column.get("boxes"),
            "start_price": _round(current_column.get("start_price"), 2),
            "end_price": _round(current_column.get("end_price"), 2),
            "trend_hint": "up" if current_column.get("type") == "X" else "down" if current_column.get("type") == "O" else None,
        },
        "recent_reversal_summary": [
            {
                "type": col.get("type"),
                "boxes": col.get("boxes"),
                "start_price": _round(col.get("start_price"), 2),
                "end_price": _round(col.get("end_price"), 2),
            }
            for col in recent_columns
        ],
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "congestion_width": targets.get("congestion_width"),
        "measured_move": targets.get("measured_move"),
        "breakout_hints": breakout_hints,
        "risk_hints": risk_hints,
        "catapult_hint": catapult_hint,
        "failed_breakout_hint": failed_breakout_hint,
        "sign_of_weakness_risk_hint": sign_of_weakness_risk_hint,
    }


def _collect_tests(
    bars: Sequence[Mapping[str, Any]],
    level: float,
    side: str,
    avg_volume: float,
) -> List[Dict[str, Any]]:
    tests: List[Dict[str, Any]] = []
    tolerance = max(level * 0.015, 1e-9)
    for bar in bars:
        ref_price = _to_float(bar.get("low")) if side == "support" else _to_float(bar.get("high"))
        if abs(ref_price - level) <= tolerance:
            penetration = ((level - ref_price) / level * 100.0) if side == "support" else ((ref_price - level) / level * 100.0)
            tests.append(
                {
                    "date": _bar_label(bar),
                    "penetration_pct": _round(penetration, 2),
                    "close_quality": _round(_bar_close_quality(bar) if side == "support" else _down_close_quality(bar), 2),
                    "volume_ratio": _round(_volume_ratio(bar, avg_volume), 2),
                }
            )
    return tests


def compute_structural_context(
    daily_bars: Any,
    weekly_bars: Any,
    monthly_bars: Any = None,
    minute_analysis: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    daily_records = _to_bar_records(daily_bars)
    weekly_records = _to_bar_records(weekly_bars)
    monthly_records = _to_bar_records(monthly_bars)
    if not daily_records:
        return {}

    recent_daily = daily_records[-min(20, len(daily_records)) :]
    daily_high = max(_to_float(bar.get("high")) for bar in recent_daily)
    daily_low = min(_to_float(bar.get("low")) for bar in recent_daily)
    daily_width = max(daily_high - daily_low, 1e-9)
    current_close = _to_float(recent_daily[-1].get("close"))
    current_position = (current_close - daily_low) / daily_width * 100.0
    avg_volume = _mean([_to_float(bar.get("volume")) for bar in recent_daily]) or 1.0
    support_tests = _collect_tests(recent_daily, daily_low, "support", avg_volume)
    resistance_tests = _collect_tests(recent_daily, daily_high, "resistance", avg_volume)

    cause_duration = 0
    for bar in reversed(daily_records[-60:]):
        close = _to_float(bar.get("close"))
        if daily_low * 0.98 <= close <= daily_high * 1.02:
            cause_duration += 1
        else:
            break

    spreads = [_bar_spread(bar) for bar in recent_daily]
    volumes = [_to_float(bar.get("volume")) for bar in recent_daily]
    spread_ratio_max = max(spreads) / max(_median(spreads), 1e-9)
    volume_ratio_max = max(volumes) / max(_median(volumes), 1e-9)
    extreme_factor = max(
        (daily_high - current_close) / daily_width if current_position > 60 else 0.0,
        (current_close - daily_low) / daily_width if current_position < 40 else 0.0,
    )
    climactic_run_score = _clamp(0.2 + min(0.35, (spread_ratio_max - 1.0) * 0.18) + min(0.25, (volume_ratio_max - 1.0) * 0.15) + 0.2 * extreme_factor)

    def _period_context(records: Sequence[Mapping[str, Any]], window: int) -> Dict[str, Any]:
        if not records:
            return {}
        recent = list(records[-min(window, len(records)) :])
        range_high = max(_to_float(bar.get("high")) for bar in recent)
        range_low = min(_to_float(bar.get("low")) for bar in recent)
        width = max(range_high - range_low, 1e-9)
        close = _to_float(recent[-1].get("close"))
        return {
            "range_high": _round(range_high, 2),
            "range_low": _round(range_low, 2),
            "current_position_pct": _round((close - range_low) / width * 100.0, 2),
            "width_pct": _round((width / max(range_low, 1e-9)) * 100.0, 2),
            "close_vs_midpoint_pct": _round(((close - ((range_high + range_low) / 2.0)) / width) * 100.0, 2),
            "bars_used": len(recent),
            "window_start": _bar_label(recent[0]),
            "window_end": _bar_label(recent[-1]),
        }

    weekly_context = _period_context(weekly_records, 20)
    monthly_context = _period_context(monthly_records, 12)
    weekly_position = _to_float(weekly_context.get("current_position_pct"), 50.0)
    monthly_position = _to_float(monthly_context.get("current_position_pct"), weekly_position if weekly_context else 50.0)

    minute_close_position = None
    minute_confirmation_score = 0.3
    if minute_analysis and not minute_analysis.get("error"):
        minute_close_position = _to_float(minute_analysis.get("close_position")) * 100.0
        above_vwap = minute_analysis.get("vs_vwap") == "above"
        minute_confirmation_score = _clamp(
            0.25
            + 0.4 * (_to_float(minute_analysis.get("close_position")) if minute_analysis.get("close_position") is not None else 0.5)
            + (0.2 if above_vwap else 0.0)
        )

    gaps = [abs(current_position - weekly_position)]
    if monthly_context:
        gaps.append(abs(weekly_position - monthly_position))
    alignment_score = _clamp(1.0 - _mean(gaps) / 100.0)
    if minute_close_position is not None:
        minute_daily_gap = abs(minute_close_position - current_position) / 100.0
        alignment_score = _clamp((alignment_score * 0.6) + (minute_confirmation_score * 0.25) + ((1.0 - minute_daily_gap) * 0.15))

    alignment_label = "mixed"
    if alignment_score >= 0.75:
        alignment_label = "aligned"
    elif alignment_score >= 0.55:
        alignment_label = "partially_aligned"

    return {
        "trading_range": {
            "high": _round(daily_high, 2),
            "low": _round(daily_low, 2),
            "mid": _round((daily_high + daily_low) / 2.0, 2),
            "width_pct": _round((daily_width / max(daily_low, 1e-9)) * 100.0, 2),
            "current_position_pct": _round(current_position, 2),
            "position_bucket": "low" if current_position < 33 else "mid" if current_position < 66 else "high",
        },
        "support_resistance_tests": {
            "support_test_count": len(support_tests),
            "resistance_test_count": len(resistance_tests),
            "last_3_tests_comparison": {
                "support": support_tests[-3:],
                "resistance": resistance_tests[-3:],
            },
        },
        "cause_building_duration_bars": cause_duration,
        "climactic_run_score": _round(climactic_run_score, 4),
        "weekly_context": weekly_context,
        "higher_timeframe_context": {
            "monthly_context": monthly_context,
        },
        "multi_timeframe_alignment": {
            "alignment_score": _round(alignment_score, 4),
            "label": alignment_label,
            "label_zh": ALIGNMENT_LABELS_ZH[alignment_label],
            "daily_position_pct": _round(current_position, 2),
            "weekly_position_pct": _round(weekly_position, 2),
            "monthly_position_pct": _round(monthly_position, 2) if monthly_context else None,
            "minute_close_position_pct": _round(minute_close_position, 2) if minute_close_position is not None else None,
            "minute_confirmation_score": _round(minute_confirmation_score, 4),
            "periods_used": ["daily", "weekly"] + (["monthly"] if monthly_context else []) + (["5m"] if minute_close_position is not None else []),
        },
    }

def build_llm_digest(
    structural_context: Mapping[str, Any],
    event_candidates: Sequence[Mapping[str, Any]],
    swing_comparisons: Sequence[Mapping[str, Any]],
    effort_result: Mapping[str, Any],
    absorption: Mapping[str, Any],
    point_figure_summary: Mapping[str, Any],
    raw_market_facts: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    top_events = sorted(
        [event for event in event_candidates if event.get("candidate")],
        key=lambda event: _to_float(event.get("score")),
        reverse=True,
    )[:5]
    latest_daily_swings = [swing for swing in swing_comparisons if swing.get("timeframe") == "daily"][-2:]
    range_state = structural_context.get("trading_range", {})
    alignment = structural_context.get("multi_timeframe_alignment", {})
    monthly_context = structural_context.get("higher_timeframe_context", {}).get("monthly_context", {})
    price_snapshot = (raw_market_facts or {}).get("price_snapshot", {})
    live_session = (raw_market_facts or {}).get("live_session", {})

    bullish_codes = {"Spring", "Shakeout", "Test", "SOS", "LPS", "SC", "PS"}
    bearish_codes = {"UT", "UTAD", "SOW", "LPSY", "BC", "PSY"}
    bullish_score = sum(_to_float(event.get("score")) for event in top_events if event.get("event_code") in bullish_codes)
    bearish_score = sum(_to_float(event.get("score")) for event in top_events if event.get("event_code") in bearish_codes)
    bullish_score += _to_float(absorption.get("breakout_acceptance_score")) + _to_float(absorption.get("demand_absorption_score"))
    bearish_score += _to_float(absorption.get("breakdown_acceptance_score")) + _to_float(absorption.get("breakout_rejection_score"))
    bias = "neutral"
    if bullish_score - bearish_score >= 0.35:
        bias = "bullish"
    elif bearish_score - bullish_score >= 0.35:
        bias = "bearish"

    top_event_score = max((_to_float(event.get("score")) for event in top_events), default=0.0)
    confidence = _round(
        _clamp(
            0.35
            + 0.3 * _to_float(alignment.get("alignment_score"), 0.0)
            + 0.2 * top_event_score
        ),
        4,
    )

    hypotheses = [{
        "bias": bias,
        "bias_zh": BIAS_LABELS_ZH[bias],
        "confidence": confidence,
        "thesis": (
            f"当前位于区间{POSITION_BUCKET_LABELS_ZH.get(range_state.get('position_bucket'), range_state.get('position_bucket'))}，且多周期{ALIGNMENT_LABELS_ZH.get(alignment.get('label'), alignment.get('label'))}"
        ),
        "drivers": [
            f"主导事件={top_events[0].get('name')} {top_events[0].get('timeframe')} score={top_events[0].get('score')}" if top_events else "主导事件=无",
            f"接受度={absorption.get('breakout_acceptance_score')}/{absorption.get('breakout_rejection_score')}",
            f"努力结果背离={effort_result.get('effort_result_divergence')}",
        ],
        "invalidation": (
            "若出现跟进失败或反向接受，则当前判断失效"
            if not absorption.get("follow_through_failure")
            else "当前判断已被跟进失败削弱"
        ),
    }]

    risk_flags: List[str] = []
    if effort_result.get("high_volume_no_progress"):
        risk_flags.append("放量无进展")
    if effort_result.get("low_volume_pullback"):
        risk_flags.append("缩量回踩")
    if absorption.get("follow_through_failure"):
        risk_flags.append("跟进失败")
    if point_figure_summary.get("failed_breakout_hint"):
        risk_flags.append("点数图失败突破")
    if point_figure_summary.get("sign_of_weakness_risk_hint"):
        risk_flags.append("点数图弱势征兆")

    compact_take = (
        f"{BIAS_LABELS_ZH[bias]}，区间位置={range_state.get('current_position_pct')}%，"
        f"多周期={ALIGNMENT_LABELS_ZH.get(alignment.get('label'), alignment.get('label'))}，"
        f"主导事件={top_events[0].get('name') if top_events else '无'}，"
        f"盘中状态={'是' if live_session.get('is_live_session') else '否'}。"
    )

    return {
        "template_version": "llm-digest-v2",
        "snapshot": {
            "current_price": price_snapshot.get("current"),
            "change_pct": price_snapshot.get("change_pct"),
            "range_position_pct": range_state.get("current_position_pct"),
            "position_bucket": range_state.get("position_bucket"),
            "position_bucket_zh": POSITION_BUCKET_LABELS_ZH.get(range_state.get("position_bucket"), range_state.get("position_bucket")),
            "alignment_label": alignment.get("label"),
            "alignment_label_zh": ALIGNMENT_LABELS_ZH.get(alignment.get("label"), alignment.get("label")),
            "alignment_score": alignment.get("alignment_score"),
            "is_live_session": live_session.get("is_live_session", False),
            "price_source": live_session.get("source", "daily_close"),
        },
        "dominant_hypotheses": hypotheses,
        "event_stack": [
            {
                "event_code": event.get("event_code"),
                "name": event.get("name"),
                "timeframe": event.get("timeframe"),
                "score": event.get("score"),
                "evidence": (event.get("evidence") or [])[:2],
            }
            for event in top_events
        ],
        "context_chain": {
            "structural": [
                f"range_position={range_state.get('current_position_pct')}%",
                f"周线同向={ALIGNMENT_LABELS_ZH.get(alignment.get('label'), alignment.get('label'))}:{alignment.get('alignment_score')}",
                f"月线位置={monthly_context.get('current_position_pct')}" if monthly_context else "月线位置=无",
            ],
            "swings": [
                {
                    "direction": swing.get("direction"),
                    "amplitude_pct": swing.get("amplitude_pct"),
                    "duration_bars": swing.get("duration_bars"),
                    "efficiency": swing.get("efficiency"),
                }
                for swing in latest_daily_swings
            ],
            "effort_result": {
                "divergence": effort_result.get("effort_result_divergence"),
                "breakout_efficiency": effort_result.get("breakout_efficiency"),
                "reversal_efficiency": effort_result.get("reversal_efficiency"),
            },
            "acceptance": {
                "breakout_acceptance": absorption.get("breakout_acceptance_score"),
                "breakout_rejection": absorption.get("breakout_rejection_score"),
                "breakdown_acceptance": absorption.get("breakdown_acceptance_score"),
                "breakdown_rejection": absorption.get("breakdown_rejection_score"),
                "test_quality": absorption.get("test_quality"),
            },
            "pnf": {
                "breakout_hints": point_figure_summary.get("breakout_hints"),
                "risk_hints": point_figure_summary.get("risk_hints"),
            },
        },
        "risk_flags": risk_flags,
        "compact_take": compact_take,
    }


def build_inference_inputs(
    structural_context: Mapping[str, Any],
    event_candidates: Sequence[Mapping[str, Any]],
    swing_comparisons: Sequence[Mapping[str, Any]],
    effort_result: Mapping[str, Any],
    absorption: Mapping[str, Any],
    point_figure_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    top_events = sorted(
        [
            {
                "event_code": event.get("event_code"),
                "name": event.get("name"),
                "timeframe": event.get("timeframe"),
                "score": event.get("score"),
            }
            for event in event_candidates
            if event.get("candidate")
        ],
        key=lambda event: _to_float(event.get("score")),
        reverse=True,
    )[:6]
    latest_swings = swing_comparisons[-3:]

    return {
        "range_state": {
            "position_bucket": structural_context.get("trading_range", {}).get("position_bucket"),
            "current_position_pct": structural_context.get("trading_range", {}).get("current_position_pct"),
            "alignment_label": structural_context.get("multi_timeframe_alignment", {}).get("label"),
            "alignment_label_zh": structural_context.get("multi_timeframe_alignment", {}).get("label_zh"),
        },
        "top_events": top_events,
        "recent_swings": latest_swings,
        "effort_result_flags": {
            key: effort_result.get(key)
            for key in (
                "high_volume_no_progress",
                "low_volume_pullback",
                "spread_volume_ratio",
                "breakout_efficiency",
                "reversal_efficiency",
            )
        },
        "acceptance_flags": {
            key: absorption.get(key)
            for key in (
                "breakout_acceptance_score",
                "breakout_rejection_score",
                "breakdown_acceptance_score",
                "breakdown_rejection_score",
                "follow_through_failure",
                "test_quality",
            )
        },
        "point_and_figure_hints": {
            "breakout_hints": point_figure_summary.get("breakout_hints"),
            "risk_hints": point_figure_summary.get("risk_hints"),
            "catapult_hint": point_figure_summary.get("catapult_hint"),
            "failed_breakout_hint": point_figure_summary.get("failed_breakout_hint"),
            "sign_of_weakness_risk_hint": point_figure_summary.get("sign_of_weakness_risk_hint"),
        },
        "higher_timeframe_context": structural_context.get("higher_timeframe_context", {}),
    }


def build_raw_market_facts(
    symbol: str,
    analysis_mode: str,
    daily_bars: Sequence[Mapping[str, Any]],
    weekly_bars: Sequence[Mapping[str, Any]],
    monthly_bars: Sequence[Mapping[str, Any]],
    key_levels: Optional[Mapping[str, Any]],
    volume_profile: Optional[Mapping[str, Any]],
    minute_analysis: Optional[Mapping[str, Any]],
    live_session: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    derived_key_levels = dict(key_levels or _derive_key_levels(daily_bars))
    daily_dates = {
        "start": _bar_label(daily_bars[0]) if daily_bars else None,
        "end": _bar_label(daily_bars[-1]) if daily_bars else None,
        "bars": len(daily_bars),
    }
    weekly_dates = {
        "start": _bar_label(weekly_bars[0]) if weekly_bars else None,
        "end": _bar_label(weekly_bars[-1]) if weekly_bars else None,
        "bars": len(weekly_bars),
    }
    monthly_dates = {
        "start": _bar_label(monthly_bars[0]) if monthly_bars else None,
        "end": _bar_label(monthly_bars[-1]) if monthly_bars else None,
        "bars": len(monthly_bars),
    }
    minute_payload = dict(minute_analysis or {})
    if minute_payload:
        minute_payload.pop("dominant", None)
        minute_payload.pop("day_type", None)
        minute_payload.pop("phases", None)

    return {
        "symbol": symbol,
        "analysis_mode": analysis_mode,
        "price_snapshot": {
            "current": derived_key_levels.get("current"),
            "prev_close": derived_key_levels.get("prev_close"),
            "change_pct": derived_key_levels.get("change_pct"),
        },
        "range_snapshot": {
            "high_20d": derived_key_levels.get("tr_high_20d"),
            "low_20d": derived_key_levels.get("tr_low_20d"),
            "mid_20d": derived_key_levels.get("tr_mid"),
            "position_pct": derived_key_levels.get("tr_position_pct"),
        },
        "live_session": dict(live_session or {}),
        "volume_profile": dict(volume_profile or {}),
        "minute_last_day": minute_payload,
        "daily_window": daily_dates,
        "weekly_window": weekly_dates,
        "monthly_window": monthly_dates,
    }


def build_wyckoff_analysis(
    symbol: str,
    analysis_mode: str,
    daily_bars: Any,
    weekly_bars: Any,
    minute_bars: Any,
    key_levels: Optional[Mapping[str, Any]] = None,
    volume_profile: Optional[Mapping[str, Any]] = None,
    minute_analysis: Optional[Mapping[str, Any]] = None,
    point_figure: Optional[Mapping[str, Any]] = None,
    data_quality: Optional[Mapping[str, Any]] = None,
    execution_time_ms: Optional[float] = None,
) -> Dict[str, Any]:
    daily_records = _to_bar_records(daily_bars)
    minute_records = _to_bar_records(minute_bars)
    effective_key_levels = dict(key_levels or _derive_key_levels(daily_records))
    live_session = build_live_session_overlay(
        daily_bars=daily_records,
        minute_bars=minute_records,
        minute_analysis=minute_analysis,
        key_levels=effective_key_levels,
    )
    effective_daily_records = merge_live_session_into_daily_records(
        daily_bars=daily_records,
        live_session=live_session,
        minute_analysis=minute_analysis,
    )
    effective_weekly_records = build_period_records_from_daily(effective_daily_records, "weekly")
    effective_monthly_records = build_period_records_from_daily(effective_daily_records, "monthly")
    effective_key_levels = dict(key_levels or _derive_key_levels(effective_daily_records))
    effective_key_levels = apply_live_session_overlay_to_key_levels(effective_key_levels, live_session)

    raw_market_facts = build_raw_market_facts(
        symbol=symbol,
        analysis_mode=analysis_mode,
        daily_bars=effective_daily_records,
        weekly_bars=effective_weekly_records,
        monthly_bars=effective_monthly_records,
        key_levels=effective_key_levels,
        volume_profile=volume_profile,
        minute_analysis=minute_analysis,
        live_session=live_session,
    )
    structural_context = compute_structural_context(
        effective_daily_records,
        effective_weekly_records,
        effective_monthly_records,
        minute_analysis,
    )
    trading_range = structural_context.get("trading_range", {})
    daily_range_low = _to_float(trading_range.get("low"))
    daily_range_high = _to_float(trading_range.get("high"))

    event_candidates: List[Dict[str, Any]] = []
    event_candidates.extend(detect_event_candidates(effective_daily_records[-40:], "daily", daily_range_low, daily_range_high))
    if effective_weekly_records:
        weekly_context = structural_context.get("weekly_context", {})
        event_candidates.extend(
            detect_event_candidates(
                effective_weekly_records[-30:],
                "weekly",
                _to_float(weekly_context.get("range_low")),
                _to_float(weekly_context.get("range_high")),
            )
        )
    if effective_monthly_records:
        monthly_context = structural_context.get("higher_timeframe_context", {}).get("monthly_context", {})
        event_candidates.extend(
            detect_event_candidates(
                effective_monthly_records[-24:],
                "monthly",
                _to_float(monthly_context.get("range_low")),
                _to_float(monthly_context.get("range_high")),
            )
        )
    if minute_records:
        minute_high = max(_to_float(bar.get("high")) for bar in minute_records[-48:])
        minute_low = min(_to_float(bar.get("low")) for bar in minute_records[-48:])
        event_candidates.extend(detect_event_candidates(minute_records[-48:], "5m", minute_low, minute_high))

    swing_comparisons: List[Dict[str, Any]] = []
    swing_comparisons.extend(compute_swing_metrics(effective_daily_records[-60:], timeframe="daily"))
    if effective_weekly_records:
        swing_comparisons.extend(compute_swing_metrics(effective_weekly_records[-40:], timeframe="weekly"))
    if effective_monthly_records:
        swing_comparisons.extend(compute_swing_metrics(effective_monthly_records[-24:], timeframe="monthly"))
    if minute_records:
        swing_comparisons.extend(compute_swing_metrics(minute_records[-48:], timeframe="5m"))

    effort_result = compute_effort_result_metrics(
        effective_daily_records[-12:],
        breakout_level=daily_range_high,
        breakdown_level=daily_range_low,
    )
    absorption = compute_absorption_scores(
        effective_daily_records[-20:],
        range_low=daily_range_low,
        range_high=daily_range_high,
    )
    point_figure_summary = summarize_point_figure(point_figure)
    inference_inputs = build_inference_inputs(
        structural_context,
        event_candidates,
        swing_comparisons,
        effort_result,
        absorption,
        point_figure_summary,
    )
    llm_digest = build_llm_digest(
        structural_context,
        event_candidates,
        swing_comparisons,
        effort_result,
        absorption,
        point_figure_summary,
        raw_market_facts=raw_market_facts,
    )

    package = WyckoffEvidencePackage(
        symbol=symbol,
        analysis_mode=analysis_mode,
        schema_version="1.0.1",
        key_levels=effective_key_levels,
        raw_market_facts=raw_market_facts,
        structural_context=structural_context,
        event_candidates=[EventCandidateModel(**event) for event in event_candidates],
        swing_comparisons=[SwingMetricModel(**swing) for swing in swing_comparisons],
        effort_result=effort_result,
        absorption_and_acceptance=absorption,
        point_and_figure_summary=point_figure_summary,
        inference_inputs=inference_inputs,
        llm_digest=llm_digest,
        data_quality=dict(data_quality or {}),
        execution_time_ms=_round(execution_time_ms, 1) if execution_time_ms is not None else None,
    )
    return package.to_dict()

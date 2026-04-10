import unittest


class WyckoffEngineV2Tests(unittest.TestCase):
    def test_imports_new_engine_module(self):
        from wyckoff_engine_v2 import detect_event_candidates  # noqa: F401

    def test_detects_spring_candidate_from_daily_bars(self):
        from wyckoff_engine_v2 import detect_event_candidates

        bars = [
            {"date": "2026-04-01", "open": 10.4, "high": 10.8, "low": 10.2, "close": 10.6, "volume": 1000},
            {"date": "2026-04-02", "open": 10.5, "high": 10.7, "low": 10.1, "close": 10.2, "volume": 950},
            {"date": "2026-04-03", "open": 10.2, "high": 10.5, "low": 9.9, "close": 10.1, "volume": 1100},
            {"date": "2026-04-06", "open": 10.0, "high": 10.2, "low": 9.2, "close": 10.0, "volume": 2200},
            {"date": "2026-04-07", "open": 10.0, "high": 10.4, "low": 9.8, "close": 10.3, "volume": 1500},
            {"date": "2026-04-08", "open": 10.3, "high": 10.6, "low": 10.1, "close": 10.5, "volume": 1200},
        ]

        events = detect_event_candidates(bars, timeframe="daily", range_low=9.4, range_high=10.8)
        spring = next(event for event in events if event["event_code"] == "Spring")

        self.assertTrue(spring["candidate"])
        self.assertGreaterEqual(spring["score"], 0.6)
        self.assertEqual(spring["name"], "弹簧")
        self.assertTrue(any("下破支撑" in item for item in spring["evidence"]))

    def test_detects_upthrust_candidate(self):
        from wyckoff_engine_v2 import detect_event_candidates

        bars = [
            {"date": "2026-04-01", "open": 9.8, "high": 10.1, "low": 9.7, "close": 10.0, "volume": 900},
            {"date": "2026-04-02", "open": 10.0, "high": 10.4, "low": 9.9, "close": 10.3, "volume": 1000},
            {"date": "2026-04-03", "open": 10.3, "high": 10.7, "low": 10.2, "close": 10.6, "volume": 1100},
            {"date": "2026-04-06", "open": 10.6, "high": 11.3, "low": 10.5, "close": 10.6, "volume": 2400},
            {"date": "2026-04-07", "open": 10.6, "high": 10.7, "low": 10.1, "close": 10.2, "volume": 1600},
            {"date": "2026-04-08", "open": 10.2, "high": 10.3, "low": 9.9, "close": 10.0, "volume": 1400},
        ]

        events = detect_event_candidates(bars, timeframe="daily", range_low=9.7, range_high=10.9)
        upthrust = next(event for event in events if event["event_code"] == "UT")

        self.assertTrue(upthrust["candidate"])
        self.assertGreaterEqual(upthrust["score"], 0.6)
        self.assertEqual(upthrust["name"], "上冲")
        self.assertTrue(any("failed" in item.lower() or "rejection" in item.lower() for item in upthrust["evidence"]))

    def test_computes_recent_swing_metrics(self):
        from wyckoff_engine_v2 import compute_swing_metrics

        bars = [
            {"date": "2026-04-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.4, "volume": 1000},
            {"date": "2026-04-02", "open": 10.4, "high": 10.6, "low": 10.1, "close": 10.2, "volume": 900},
            {"date": "2026-04-03", "open": 10.2, "high": 10.9, "low": 10.1, "close": 10.8, "volume": 1200},
            {"date": "2026-04-06", "open": 10.8, "high": 10.9, "low": 10.0, "close": 10.1, "volume": 1500},
            {"date": "2026-04-07", "open": 10.1, "high": 10.4, "low": 9.9, "close": 10.3, "volume": 1000},
            {"date": "2026-04-08", "open": 10.3, "high": 11.1, "low": 10.2, "close": 11.0, "volume": 1800},
        ]

        swings = compute_swing_metrics(bars)

        self.assertGreaterEqual(len(swings), 2)
        self.assertIn(swings[-1]["direction"], {"up_swing", "down_swing"})
        self.assertIn("efficiency", swings[-1])

    def test_computes_effort_result_metrics(self):
        from wyckoff_engine_v2 import compute_effort_result_metrics

        bars = [
            {"date": "2026-04-01", "open": 10.0, "high": 10.8, "low": 9.9, "close": 10.7, "volume": 1000},
            {"date": "2026-04-02", "open": 10.7, "high": 10.9, "low": 10.6, "close": 10.72, "volume": 2600},
            {"date": "2026-04-03", "open": 10.72, "high": 10.75, "low": 10.5, "close": 10.54, "volume": 900},
        ]

        metrics = compute_effort_result_metrics(bars, breakout_level=10.7, breakdown_level=10.2)

        self.assertTrue(metrics["high_volume_no_progress"])
        self.assertTrue(metrics["low_volume_pullback"])
        self.assertGreaterEqual(metrics["close_quality_score"], 0.0)

    def test_computes_acceptance_and_rejection(self):
        from wyckoff_engine_v2 import compute_absorption_scores

        bars = [
            {"date": "2026-04-01", "open": 9.8, "high": 10.0, "low": 9.7, "close": 9.95, "volume": 900},
            {"date": "2026-04-02", "open": 9.95, "high": 10.3, "low": 9.9, "close": 10.25, "volume": 1400},
            {"date": "2026-04-03", "open": 10.25, "high": 10.45, "low": 10.2, "close": 10.4, "volume": 1500},
            {"date": "2026-04-06", "open": 10.4, "high": 10.42, "low": 9.98, "close": 10.02, "volume": 1700},
        ]

        scores = compute_absorption_scores(bars, range_low=9.8, range_high=10.2)

        self.assertGreater(scores["breakout_acceptance_score"], 0.5)
        self.assertGreater(scores["breakout_rejection_score"], 0.0)
        self.assertIn("test_quality", scores)

    def test_summarizes_point_and_figure_columns(self):
        from wyckoff_engine_v2 import summarize_point_figure

        point_figure = {
            "box_size": 0.5,
            "reversal_boxes": 3,
            "columns": [
                {"type": "O", "start_price": 10.0, "end_price": 8.5, "boxes": 3, "high": 10.0, "low": 8.5},
                {"type": "X", "start_price": 8.5, "end_price": 10.5, "boxes": 4, "high": 10.6, "low": 8.8},
                {"type": "O", "start_price": 10.5, "end_price": 9.0, "boxes": 3, "high": 10.4, "low": 9.0},
                {"type": "X", "start_price": 9.0, "end_price": 11.5, "boxes": 5, "high": 11.7, "low": 9.2},
            ],
            "targets": {"direction": "bullish", "measured_move": 3.0, "congestion_width": 4},
            "current_trend": "X",
            "current_column_boxes": 5,
            "ltp": 11.2,
        }

        summary = summarize_point_figure(point_figure)

        self.assertEqual(summary["current_column_summary"]["type"], "X")
        self.assertEqual(summary["bullish_count"], 2)
        self.assertIn("breakout_hints", summary)

    def test_live_session_overlay_updates_current_snapshot(self):
        from wyckoff_engine_v2 import build_wyckoff_analysis

        daily_bars = [
            {"date": "2026-04-09", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
        ]
        weekly_bars = [
            {"date": "2026-04-12", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
        ]
        minute_bars = [
            {"time": "2026-04-10 09:35:00", "open": 10.3, "high": 10.6, "low": 10.2, "close": 10.55, "volume": 5000},
            {"time": "2026-04-10 09:40:00", "open": 10.55, "high": 10.7, "low": 10.5, "close": 10.68, "volume": 6200},
        ]
        key_levels = {
            "current": 10.2,
            "prev_close": 10.0,
            "change_pct": 2.0,
            "tr_high_20d": 10.5,
            "tr_low_20d": 9.8,
            "tr_mid": 10.15,
            "tr_position_pct": 57.1,
            "ma5": 10.1,
            "ma10": 10.0,
            "ma20": 9.9,
        }
        minute_analysis = {
            "date": "2026-04-10",
            "day_close": 10.68,
            "day_high": 10.7,
            "day_low": 10.2,
            "close_position": 0.96,
            "vwap": 10.58,
            "vs_vwap": "above",
        }

        result = build_wyckoff_analysis(
            symbol="000001",
            analysis_mode="standard",
            daily_bars=daily_bars,
            weekly_bars=weekly_bars,
            minute_bars=minute_bars,
            key_levels=key_levels,
            volume_profile={},
            minute_analysis=minute_analysis,
            point_figure={},
            data_quality={},
        )

        self.assertEqual(result["raw_market_facts"]["price_snapshot"]["current"], 10.68)
        self.assertTrue(result["raw_market_facts"]["live_session"]["is_live_session"])
        self.assertEqual(result["key_levels"]["current"], 10.68)

    def test_llm_digest_uses_dense_template(self):
        from wyckoff_engine_v2 import build_llm_digest

        digest = build_llm_digest(
            structural_context={
                "trading_range": {"current_position_pct": 22.5, "position_bucket": "low", "low": 10.0, "high": 12.0},
                "multi_timeframe_alignment": {"alignment_score": 0.81, "label": "aligned"},
            },
            event_candidates=[
                {"event_code": "Spring", "name": "弹簧", "timeframe": "daily", "score": 0.82, "candidate": True, "evidence": ["undercut support", "strong close"]},
                {"event_code": "SOS", "name": "强势征兆", "timeframe": "5m", "score": 0.67, "candidate": True, "evidence": ["strong intraday thrust"]},
                {"event_code": "UT", "name": "上冲", "timeframe": "weekly", "score": 0.25, "candidate": False, "evidence": []},
            ],
            swing_comparisons=[
                {"timeframe": "daily", "direction": "up_swing", "amplitude_pct": 6.2, "duration_bars": 4, "efficiency": 0.78},
            ],
            effort_result={
                "effort_result_divergence": 0.12,
                "spread_volume_ratio": 0.84,
                "breakout_efficiency": 0.63,
                "reversal_efficiency": 0.22,
                "high_volume_no_progress": False,
                "low_volume_pullback": True,
            },
            absorption={
                "breakout_acceptance_score": 0.58,
                "breakout_rejection_score": 0.12,
                "breakdown_acceptance_score": 0.1,
                "breakdown_rejection_score": 0.41,
                "follow_through_failure": False,
                "test_quality": 0.61,
            },
            point_figure_summary={
                "breakout_hints": ["catapult-style continuation"],
                "risk_hints": ["failed breakout risk if support breaks"],
                "catapult_hint": True,
                "failed_breakout_hint": False,
                "sign_of_weakness_risk_hint": False,
            },
            raw_market_facts={
                "price_snapshot": {"current": 10.68, "change_pct": 4.7},
                "live_session": {"is_live_session": True, "source": "minute_last_day", "session_date": "2026-04-10"},
            },
        )

        self.assertEqual(digest["template_version"], "llm-digest-v2")
        self.assertIn("snapshot", digest)
        self.assertIn("dominant_hypotheses", digest)
        self.assertIn("event_stack", digest)
        self.assertIn("compact_take", digest)
        self.assertEqual(digest["event_stack"][0]["name"], "弹簧")

    def test_live_session_recalculates_range_position_and_phase_inputs(self):
        from wyckoff_engine_v2 import build_wyckoff_analysis

        daily_bars = [
            {"date": "2026-04-07", "open": 10.0, "high": 10.4, "low": 9.9, "close": 10.1, "volume": 1000},
            {"date": "2026-04-08", "open": 10.1, "high": 10.2, "low": 9.8, "close": 9.9, "volume": 900},
            {"date": "2026-04-09", "open": 9.9, "high": 10.0, "low": 9.7, "close": 9.8, "volume": 950},
        ]
        weekly_bars = [
            {"date": "2026-04-12", "open": 10.0, "high": 10.4, "low": 9.7, "close": 9.8, "volume": 3000},
        ]
        minute_bars = [
            {"time": "2026-04-10 09:35:00", "open": 10.1, "high": 10.7, "low": 10.0, "close": 10.65, "volume": 5000},
            {"time": "2026-04-10 09:40:00", "open": 10.65, "high": 10.9, "low": 10.5, "close": 10.85, "volume": 4200},
        ]
        minute_analysis = {
            "date": "2026-04-10",
            "day_high": 10.9,
            "day_low": 10.0,
            "day_close": 10.85,
            "close_position": 0.94,
            "vwap": 10.55,
            "vs_vwap": "above",
            "total_volume": 9200,
        }

        result = build_wyckoff_analysis(
            symbol="000002",
            analysis_mode="standard",
            daily_bars=daily_bars,
            weekly_bars=weekly_bars,
            minute_bars=minute_bars,
            key_levels=None,
            volume_profile={},
            minute_analysis=minute_analysis,
            point_figure={},
            data_quality={},
        )

        self.assertGreater(result["raw_market_facts"]["range_snapshot"]["position_pct"], 80)
        self.assertGreater(result["structural_context"]["trading_range"]["current_position_pct"], 80)
        self.assertGreater(result["structural_context"]["weekly_context"]["current_position_pct"], 80)

    def test_output_drops_legacy_fields(self):
        from wyckoff_engine_v2 import build_wyckoff_analysis

        result = build_wyckoff_analysis(
            symbol="000003",
            analysis_mode="standard",
            daily_bars=[{"date": "2026-04-09", "open": 10.0, "high": 10.3, "low": 9.8, "close": 10.1, "volume": 1000}],
            weekly_bars=[{"date": "2026-04-12", "open": 10.0, "high": 10.3, "low": 9.8, "close": 10.1, "volume": 1000}],
            minute_bars=[],
            minute_analysis={"error": "No minute data"},
            point_figure={},
            data_quality={},
        )

        self.assertNotIn("trend", result)
        self.assertNotIn("phase", result)
        self.assertNotIn("probabilities", result)
        self.assertNotIn("optional_legacy_outputs", result)
        self.assertNotIn("deprecated_fields", result)


if __name__ == "__main__":
    unittest.main()

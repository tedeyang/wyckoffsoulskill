import argparse
import unittest
from unittest.mock import patch


class VpaCliTests(unittest.TestCase):
    def test_parser_accepts_query_without_subcommand(self):
        from vpa import build_cli_parser

        parser = build_cli_parser()
        args = parser.parse_args(["贵州茅台", "--deep"])

        self.assertEqual(args.query, "贵州茅台")
        self.assertTrue(args.deep)

    def test_run_cli_returns_candidate_matches_when_query_is_not_resolved(self):
        from vpa import run_cli

        args = argparse.Namespace(query="科技", deep=False)
        payload = {
            "success": False,
            "code": None,
            "name": None,
            "matches": [["000100", "TCL科技"]],
            "message": "'科技' 可能指以下股票，请确认：",
            "requires_clarification": True,
        }

        with patch("vpa.resolve_stock_code", return_value=payload), patch("vpa._print_json") as print_json:
            exit_code = run_cli(args)

        self.assertEqual(exit_code, 1)
        print_json.assert_called_once()
        actual_payload = print_json.call_args.kwargs.get("payload")
        if actual_payload is None:
            actual_payload = print_json.call_args.args[0]
        self.assertEqual(actual_payload["matches"], payload["matches"])
        self.assertTrue(actual_payload["message"].endswith("请用更准确的股票名称或 6 位代码重试。"))

    def test_run_cli_uses_deep_flag_for_analysis(self):
        from vpa import run_cli

        args = argparse.Namespace(query="600519", deep=True)
        resolved = {
            "success": True,
            "code": "600519",
            "name": "贵州茅台",
            "matches": [],
            "message": "已定位: 贵州茅台 (600519)",
            "requires_clarification": False,
        }
        result = {"symbol": "600519", "schema_version": "1.0.2"}
        compact = {"symbol": "600519", "schema_version": "1.0.2", "output_mode": "compact"}

        with patch("vpa.resolve_stock_code", return_value=resolved), patch(
            "vpa.quick_analysis_v2", return_value=result
        ) as analyze, patch("vpa._compact_analysis_result", return_value=compact), patch("vpa._print_json") as print_json:
            exit_code = run_cli(args)

        self.assertEqual(exit_code, 0)
        analyze.assert_called_once_with("600519", analysis_mode="deep")
        print_json.assert_called_once_with(compact, pretty=False)


if __name__ == "__main__":
    unittest.main()

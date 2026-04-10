"""Single-entry CLI for the Wyckoff VPA engine."""

from __future__ import annotations

import argparse

from akshare_fetcher import _compact_analysis_result, _print_json, quick_analysis_v2, resolve_stock_code


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a Chinese A-share by stock name or 6-digit code",
    )
    parser.add_argument("query", help="Stock name or 6-digit code")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Use deeper history for long-term analysis",
    )
    return parser


def _resolution_failure_payload(resolved: dict) -> dict:
    payload = dict(resolved)
    message = payload.get("message") or "未找到匹配股票"
    if not message.endswith(("。", "！", "？", "：", ".", "!", "?", ":")):
        message = f"{message}。"
    payload["message"] = f"{message} 请用更准确的股票名称或 6 位代码重试。"
    return payload


def run_cli(args: argparse.Namespace) -> int:
    resolved = resolve_stock_code(args.query)
    if not resolved.get("success"):
        _print_json(_resolution_failure_payload(resolved), pretty=False)
        return 1

    symbol = resolved["code"]
    analysis_mode = "deep" if args.deep else "standard"

    try:
        result = quick_analysis_v2(symbol, analysis_mode=analysis_mode)
        payload = _compact_analysis_result(result)
        _print_json(payload, pretty=False)
        return 0
    except Exception as exc:
        error_payload = {
            "success": False,
            "code": symbol,
            "name": resolved.get("name"),
            "error": str(exc),
        }
        _print_json(error_payload, pretty=False)
        return 1


def main() -> int:
    parser = build_cli_parser()
    cli_args = parser.parse_args()
    return run_cli(cli_args)


if __name__ == "__main__":
    raise SystemExit(main())

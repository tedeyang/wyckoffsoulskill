"""
Standalone CLI entrypoint for the Wyckoff VPA engine.
"""

import argparse

from akshare_fetcher import _compact_analysis_result, _print_json, quick_analysis_v2, resolve_stock_code


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wyckoff VPA CLI for Chinese A-shares (JSON output)"
    )
    subparsers = parser.add_subparsers(dest="command")

    resolve_parser = subparsers.add_parser(
        "resolve", help="Resolve stock code/name/alias and return JSON"
    )
    resolve_parser.add_argument("query", help="Stock query (name/alias/code)")
    resolve_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Run Wyckoff analysis and return JSON result"
    )
    analyze_parser.add_argument("query", help="Stock query (name/alias/code)")
    analyze_parser.add_argument(
        "--analysis-mode",
        "-m",
        choices=["standard", "deep"],
        default="standard",
        help="Analysis mode: standard(200d/100w) or deep(500d/200w)",
    )
    analyze_parser.add_argument(
        "--full",
        action="store_true",
        help="Return full evidence package payload",
    )
    analyze_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    if args.command == "resolve":
        result = resolve_stock_code(args.query)
        _print_json(result, pretty=args.pretty)
        return 0 if result.get("success") else 1

    if args.command == "analyze":
        resolved = resolve_stock_code(args.query)
        if not resolved.get("success"):
            _print_json(resolved, pretty=args.pretty)
            return 1

        symbol = resolved["code"]
        try:
            result = quick_analysis_v2(symbol, analysis_mode=args.analysis_mode)
            payload = result if args.full else _compact_analysis_result(result)
            _print_json(payload, pretty=args.pretty)
            return 0
        except Exception as exc:
            error_payload = {
                "success": False,
                "code": symbol,
                "name": resolved.get("name"),
                "error": str(exc),
            }
            _print_json(error_payload, pretty=args.pretty)
            return 1

    return 1


def main() -> int:
    parser = build_cli_parser()
    cli_args = parser.parse_args()
    if not cli_args.command:
        parser.print_help()
        return 1
    return run_cli(cli_args)


if __name__ == "__main__":
    raise SystemExit(main())

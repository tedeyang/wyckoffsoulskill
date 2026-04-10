"""Install the Wyckoff VPA runtime and per-agent adapters."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
import venv
from pathlib import Path
from typing import Iterable, Sequence

from __version__ import __version__


SKILL_NAME = "wyckoff-vpa"
SUPPORTED_TARGETS = ("codex", "claudecode", "kimi", "openclaw")
CORE_FILES = (
    "SKILL.md",
    "README.md",
    "requirements.txt",
    "__version__.py",
    "vpa.py",
    "akshare_fetcher.py",
    "wyckoff_engine_v2.py",
    "stock_constants.py",
    "generate_stock_constants.py",
)


def resolve_targets(targets: str | Sequence[str]) -> list[str]:
    if isinstance(targets, str):
        raw_items = [item.strip().lower() for item in targets.split(",") if item.strip()]
    else:
        raw_items = [str(item).strip().lower() for item in targets if str(item).strip()]

    if not raw_items:
        raise ValueError("At least one target is required")
    if "all" in raw_items:
        return list(SUPPORTED_TARGETS)

    invalid = [item for item in raw_items if item not in SUPPORTED_TARGETS]
    if invalid:
        raise ValueError(f"Unsupported target(s): {', '.join(invalid)}")

    ordered: list[str] = []
    for item in raw_items:
        if item not in ordered:
            ordered.append(item)
    return ordered


def default_runtime_root() -> Path:
    return Path.home() / ".wyckoff-vpa"


def default_adapter_dir(target: str) -> Path | None:
    if target == "codex":
        return Path.home() / ".codex" / "skills" / SKILL_NAME
    if target == "claudecode":
        return Path.home() / ".claude" / "skills" / SKILL_NAME
    return None


def launcher_path(runtime_root: Path) -> Path:
    return runtime_root / "bin" / "wyckoff-vpa"


def _copy_core_files(source_root: Path, runtime_root: Path) -> None:
    app_root = runtime_root / "app"
    app_root.mkdir(parents=True, exist_ok=True)

    for relative_name in CORE_FILES:
        source = source_root / relative_name
        destination = app_root / relative_name
        shutil.copy2(source, destination)


def _python_executable(runtime_root: Path) -> Path:
    if os.name == "nt":
        return runtime_root / ".venv" / "Scripts" / "python.exe"
    return runtime_root / ".venv" / "bin" / "python"


def _create_venv(runtime_root: Path) -> None:
    builder = venv.EnvBuilder(with_pip=True, clear=False)
    builder.create(runtime_root / ".venv")


def _install_dependencies(runtime_root: Path) -> None:
    python_bin = _python_executable(runtime_root)
    requirements = runtime_root / "app" / "requirements.txt"
    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "-r", str(requirements)],
        check=True,
    )


def _write_launcher(runtime_root: Path) -> Path:
    bin_dir = runtime_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = launcher_path(runtime_root)
    app_dir = runtime_root / "app"
    venv_python = _python_executable(runtime_root)
    fallback = "python" if os.name == "nt" else "python3"

    if os.name == "nt":
        content = textwrap.dedent(
            f"""\
            @echo off
            setlocal
            set "RUNTIME_ROOT={runtime_root}"
            set "APP_DIR={app_dir}"
            if exist "{venv_python}" (
              "{venv_python}" "%APP_DIR%\\vpa.py" %*
            ) else (
              {fallback} "%APP_DIR%\\vpa.py" %*
            )
            """
        )
    else:
        content = textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            RUNTIME_ROOT="{runtime_root}"
            APP_DIR="{app_dir}"
            if [[ -x "{venv_python}" ]]; then
              exec "{venv_python}" "$APP_DIR/vpa.py" "$@"
            fi
            exec {fallback} "$APP_DIR/vpa.py" "$@"
            """
        )

    launcher.write_text(content, encoding="utf-8")
    if os.name != "nt":
        launcher.chmod(0o755)
    return launcher


def _codex_skill_text(command: Path, target: str) -> str:
    description_target = "Codex" if target == "codex" else "Claude Code"
    return textwrap.dedent(
        f"""\
        ---
        name: wyckoff-vpa
        description: Use when analyzing Chinese A-shares, judging whether a stock is buyable, or explaining Wyckoff/VPA output with multi-timeframe context and 5-minute execution confirmation in {description_target}.
        ---

        # Wyckoff VPA

        Use the installed launcher instead of repo-local Python commands.

        ## Workflow

        1. Resolve first:
           `{command} resolve "<query>"`
        2. Analyze:
           `{command} analyze "<query>"`
        3. Use `--analysis-mode deep` only for 长线 or 深度研究.

        ## Guardrails

        - If `requires_clarification=true`, ask the user to choose from `matches`.
        - During live trading, prefer `raw_market_facts.live_session` over prior close.
        - Evidence before conclusion: read `event_candidates`, `effort_result`, and `absorption_and_acceptance`.
        - Plain-language answers must avoid jargon and must not invent levels absent from the payload.
        """
    )


def _generic_prompt_text(command: Path, target: str) -> str:
    display = "Kimi" if target == "kimi" else "OpenClaw"
    return textwrap.dedent(
        f"""\
        # Wyckoff VPA Adapter For {display}

        Use the local launcher below for A-share analysis:

        - Resolve: `{command} resolve "<query>"`
        - Analyze: `{command} analyze "<query>"`
        - Deep mode: `{command} analyze "<query>" --analysis-mode deep`

        Rules:

        - Resolve first. If the response asks for clarification, do not guess.
        - Treat `raw_market_facts.live_session` as the live price source during the trading session.
        - Explain evidence before recommendations.
        - In plain-language mode, avoid jargon and do not invent support, stop, or target levels.
        """
    )


def _render_adapter(target: str, command: Path) -> tuple[str, str]:
    if target in {"codex", "claudecode"}:
        return "SKILL.md", _codex_skill_text(command, target)
    return "PROMPT.md", _generic_prompt_text(command, target)


def _write_adapters(runtime_root: Path, targets: Iterable[str], adapters_root: Path | None) -> list[Path]:
    created: list[Path] = []
    command = launcher_path(runtime_root)

    for target in targets:
        file_name, content = _render_adapter(target, command)
        destination_root = None
        if adapters_root is not None:
            destination_root = adapters_root / target
        else:
            default_root = default_adapter_dir(target)
            if default_root is not None:
                destination_root = default_root

        if destination_root is None:
            continue

        destination_root.mkdir(parents=True, exist_ok=True)
        destination = destination_root / file_name
        destination.write_text(content, encoding="utf-8")
        created.append(destination)

    return created


def install_package(
    source_root: Path,
    runtime_root: Path,
    targets: Sequence[str],
    adapters_root: Path | None = None,
    create_venv: bool = True,
    install_deps: bool = True,
) -> dict[str, object]:
    runtime_root.mkdir(parents=True, exist_ok=True)
    _copy_core_files(source_root, runtime_root)

    if create_venv:
        _create_venv(runtime_root)
        if install_deps:
            _install_dependencies(runtime_root)

    launcher = _write_launcher(runtime_root)
    created_adapters = _write_adapters(runtime_root, targets, adapters_root)

    return {
        "runtime_root": runtime_root,
        "launcher": launcher,
        "targets": list(targets),
        "adapters": created_adapters,
        "version": __version__,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the Wyckoff VPA runtime and agent adapters",
    )
    subparsers = parser.add_subparsers(dest="command")

    install_parser = subparsers.add_parser("install", help="Install runtime and adapters")
    install_parser.add_argument(
        "--target",
        default="codex",
        help="Target adapter(s): codex, claudecode, kimi, openclaw, all, or a comma-separated list",
    )
    install_parser.add_argument(
        "--runtime-root",
        type=Path,
        default=default_runtime_root(),
        help="Directory for the shared runtime bundle",
    )
    install_parser.add_argument(
        "--adapters-root",
        type=Path,
        default=None,
        help="Optional directory to write target adapters into; defaults to platform-specific paths when available",
    )
    install_parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Skip virtual environment creation",
    )
    install_parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency installation even when a virtual environment is created",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "install":
        parser.print_help()
        return 1

    targets = resolve_targets(args.target)
    result = install_package(
        source_root=Path(__file__).resolve().parents[1],
        runtime_root=args.runtime_root,
        targets=targets,
        adapters_root=args.adapters_root,
        create_venv=not args.skip_venv,
        install_deps=not args.skip_deps,
    )

    print(f"Installed Wyckoff VPA {result['version']} into {result['runtime_root']}")
    print(f"Launcher: {result['launcher']}")
    if result["adapters"]:
        print("Adapters:")
        for adapter in result["adapters"]:
            print(f"  - {adapter}")
    else:
        print("No adapters were written automatically. Pass --adapters-root for manual export targets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

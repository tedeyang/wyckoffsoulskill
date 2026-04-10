"""Build a distributable release archive for the Wyckoff VPA package."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Iterable

from __version__ import __version__


ARCHIVE_ROOT = "wyckoff-vpa"
INCLUDE_PATHS = (
    ".github/workflows/release.yml",
    "SKILL.md",
    "README.md",
    "__version__.py",
    "requirements.txt",
    "vpa.py",
    "akshare_fetcher.py",
    "wyckoff_engine_v2.py",
    "stock_constants.py",
    "generate_stock_constants.py",
    "installer",
    "tests/test_installer.py",
)


def _iter_files(source_root: Path) -> Iterable[Path]:
    for relative_name in INCLUDE_PATHS:
        path = source_root / relative_name
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and "__pycache__" not in child.parts:
                    yield child
        elif path.is_file():
            yield path


def build_release_archive(source_root: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{ARCHIVE_ROOT}-{__version__}.zip"

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in _iter_files(source_root):
            relative_path = file_path.relative_to(source_root)
            archive.write(file_path, arcname=f"{ARCHIVE_ROOT}/{relative_path.as_posix()}")

    return archive_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Wyckoff VPA release zip")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dist",
        help="Directory for the generated archive",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    source_root = Path(__file__).resolve().parents[1]
    archive = build_release_archive(source_root, args.output_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

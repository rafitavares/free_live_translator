#!/usr/bin/env python3
"""Write one installer progress checkpoint for shell/PowerShell wrappers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.install_progress import write_install_progress  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("percent", type=float)
    parser.add_argument("phase")
    parser.add_argument("detail", nargs="?", default="")
    parser.add_argument("--item-index", type=int, default=0)
    parser.add_argument("--item-count", type=int, default=0)
    parser.add_argument("--indeterminate", action="store_true")
    args = parser.parse_args()
    write_install_progress(
        args.percent,
        args.phase,
        args.detail,
        item_index=args.item_index,
        item_count=args.item_count,
        indeterminate=args.indeterminate,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

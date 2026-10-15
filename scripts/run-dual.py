#!/usr/bin/env python3
"""Compatibility wrapper for the stable Church Cap engine entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure relative paths are stable even if launched from another directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.entrypoint import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Church Cap's local environment was not found. Run setup first."
  exit 1
fi

cd "$ROOT"
"$PYTHON" "$ROOT/scripts/report-install-progress.py" 2 dependencies "Preparing the local speech runtime."
"$PYTHON" -m pip install -r "$ROOT/requirements-tts.txt"
"$PYTHON" "$ROOT/scripts/report-install-progress.py" 8 voices "Speech runtime ready; preparing selected voice packs."
"$PYTHON" "$ROOT/scripts/install-tts-voices.py" "$@"

#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEFAULT_PACKAGING_PYTHON="python3.12"
if [[ -x "$PROJECT_ROOT/.venv-packaging/bin/python" ]]; then
  DEFAULT_PACKAGING_PYTHON="$PROJECT_ROOT/.venv-packaging/bin/python"
fi
PACKAGING_PYTHON="${CHURCH_CAP_PACKAGING_PYTHON:-$DEFAULT_PACKAGING_PYTHON}"
export CHURCH_CAP_PACKAGING_PYTHON="$PACKAGING_PYTHON"
# Keep PyInstaller's bootloader/cache state local to this ignored build tree.
# This avoids hidden dependence on a developer's global Library cache and
# makes CI and clean-room reproduction easier to reason about.
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PROJECT_ROOT/build/pyinstaller-config}"
"$PROJECT_ROOT/scripts/release/check-macos-packaging-host.sh"

if ! "$PACKAGING_PYTHON" -c 'import PyInstaller' >/dev/null 2>&1; then
  echo "PyInstaller is missing from the packaging environment. Install requirements-packaged.txt first." >&2
  exit 1
fi

cd "$PROJECT_ROOT"
"$PACKAGING_PYTHON" -m PyInstaller \
  --clean \
  --noconfirm \
  --distpath "$PROJECT_ROOT/dist/engine-macos-arm64" \
  --workpath "$PROJECT_ROOT/build/engine-macos-arm64" \
  "$PROJECT_ROOT/packaging/engine/church_cap_engine.spec"

ENGINE_PATH="$PROJECT_ROOT/dist/engine-macos-arm64/church-cap-engine/church-cap-engine"
PYTHON_FRAMEWORK="$PROJECT_ROOT/dist/engine-macos-arm64/church-cap-engine/_internal/Python.framework"
if [[ ! -x "$ENGINE_PATH" ]]; then
  echo "The expected frozen engine was not produced at $ENGINE_PATH." >&2
  exit 1
fi

if [[ -d "$PYTHON_FRAMEWORK" ]]; then
  "$PROJECT_ROOT/scripts/release/normalize-macos-python-framework.sh" "$PYTHON_FRAMEWORK"
  codesign --force --sign - --timestamp=none "$PYTHON_FRAMEWORK"
  codesign --verify --strict --verbose=2 "$PYTHON_FRAMEWORK"
fi

"$PROJECT_ROOT/scripts/release/check-macos-engine-bundle.sh" "$PROJECT_ROOT/dist/engine-macos-arm64/church-cap-engine"

echo "Frozen Apple Silicon engine created at: $ENGINE_PATH"

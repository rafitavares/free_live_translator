#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE_DIR="${1:-$PROJECT_ROOT/dist/engine-macos-arm64/church-cap-engine}"
ENGINE_PATH="$ENGINE_DIR/church-cap-engine"
PYTHON_FRAMEWORK="$ENGINE_DIR/_internal/Python.framework"

if [[ ! -x "$ENGINE_PATH" ]]; then
  echo "Frozen engine executable not found: $ENGINE_PATH" >&2
  exit 1
fi

required_resources=(
  "$ENGINE_DIR/_internal/LICENSE"
  "$ENGINE_DIR/_internal/app/templates/operator.html"
  "$ENGINE_DIR/_internal/app/static/styles.css"
  "$ENGINE_DIR/_internal/app/locales/client_ui.json"
  "$ENGINE_DIR/_internal/app/static/flags/LICENSE.flag-icons"
  "$ENGINE_DIR/_internal/docs/legal/THIRD_PARTY_NOTICES.md"
  "$ENGINE_DIR/_internal/docs/legal/SPOKEN_LANGUAGE_MODELS.md"
  "$ENGINE_DIR/_internal/scripts/install-tts-voices.py"
  "$ENGINE_DIR/_internal/_sounddevice_data/portaudio-binaries/libportaudio.dylib"
)

for resource in "${required_resources[@]}"; do
  if [[ ! -f "$resource" ]]; then
    echo "Required packaged resource is missing: $resource" >&2
    exit 1
  fi
done

macho_count=0
invalid_count=0
while IFS= read -r -d '' candidate; do
  description="$(file -b "$candidate")"
  if [[ "$description" != *"Mach-O"* ]]; then
    continue
  fi
  macho_count=$((macho_count + 1))
  architectures="$(lipo -archs "$candidate")"
  if [[ " $architectures " != *" arm64 "* ]]; then
    echo "Mach-O file does not contain arm64 code: $candidate ($architectures)" >&2
    invalid_count=$((invalid_count + 1))
  fi
done < <(find "$ENGINE_DIR" -type f -print0)

if (( macho_count == 0 || invalid_count != 0 )); then
  echo "Mach-O architecture validation failed ($macho_count inspected, $invalid_count invalid)." >&2
  exit 1
fi

if [[ -d "$PYTHON_FRAMEWORK" ]]; then
  [[ -L "$PYTHON_FRAMEWORK/Python" ]] || { echo "Python.framework/Python must be a symlink." >&2; exit 1; }
  [[ -L "$PYTHON_FRAMEWORK/Resources" ]] || { echo "Python.framework/Resources must be a symlink." >&2; exit 1; }
  [[ -L "$PYTHON_FRAMEWORK/Versions/Current" ]] || { echo "Python.framework/Versions/Current must be a symlink." >&2; exit 1; }
  codesign --verify --strict --verbose=2 "$PYTHON_FRAMEWORK"
  codesign --verify --strict --verbose=2 "$PYTHON_FRAMEWORK/Versions/Current/Python"
fi

codesign --verify --deep --strict --verbose=2 "$ENGINE_PATH"
CHURCH_CAP_RUNTIME_MODE=packaged CHURCH_CAP_RESOURCE_INSTALL=validate "$ENGINE_PATH"
echo "Apple Silicon engine bundle verified: $macho_count Mach-O files contain arm64 code."

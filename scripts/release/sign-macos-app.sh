#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_ROOT/scripts/release/macos-signing-identity.sh"
APP_PATH="$PROJECT_ROOT/dist/macos-arm64/Church Cap.app"
IDENTITY="${CHURCH_CAP_CODESIGN_IDENTITY:-}"
IDENTITY_SHA1="${CHURCH_CAP_CODESIGN_IDENTITY_SHA1:-}"
SIGNING_IDENTITY="$IDENTITY"
ADHOC=false

usage() {
  cat <<'EOF'
Usage: sign-macos-app.sh [--adhoc] [Church Cap.app]

Production signing requires CHURCH_CAP_CODESIGN_IDENTITY to name a valid
"Developer ID Application" identity. --adhoc is only for local structural
testing and never produces a public release artifact.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--adhoc" ]]; then
  ADHOC=true
  IDENTITY="-"
  shift
fi
if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi
if [[ $# -eq 1 ]]; then
  APP_PATH="$1"
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "Church Cap application bundle not found: $APP_PATH" >&2
  exit 1
fi
if [[ "$ADHOC" == false ]]; then
  if [[ -z "$IDENTITY" ]]; then
    echo "Set CHURCH_CAP_CODESIGN_IDENTITY to a Developer ID Application identity." >&2
    exit 1
  fi
  if ! church_cap_resolve_developer_id "$IDENTITY" "$IDENTITY_SHA1"; then
    exit 1
  fi
  SIGNING_IDENTITY="$CHURCH_CAP_RESOLVED_CODESIGN_IDENTITY"
fi

ENGINE_ENTITLEMENTS="$PROJECT_ROOT/packaging/macos/engine.entitlements"
LOCAL_ENGINE_ENTITLEMENTS="$PROJECT_ROOT/packaging/macos/engine-local-adhoc.entitlements"
SUPERVISOR_ENTITLEMENTS="$PROJECT_ROOT/packaging/macos/supervisor.entitlements"
SUPERVISOR="$APP_PATH/Contents/MacOS/church-cap-desktop"
ENGINE_ROOT="$APP_PATH/Contents/Resources/engine/church-cap-engine"
ENGINE="$ENGINE_ROOT/church-cap-engine"
PYTHON_FRAMEWORK="$ENGINE_ROOT/_internal/Python.framework"

for required in "$ENGINE_ENTITLEMENTS" "$LOCAL_ENGINE_ENTITLEMENTS" "$SUPERVISOR_ENTITLEMENTS" "$SUPERVISOR" "$ENGINE"; do
  if [[ ! -e "$required" ]]; then
    echo "Required signing input is missing: $required" >&2
    exit 1
  fi
done
plutil -lint "$ENGINE_ENTITLEMENTS" "$LOCAL_ENGINE_ENTITLEMENTS" "$SUPERVISOR_ENTITLEMENTS"

if [[ -d "$PYTHON_FRAMEWORK" ]]; then
  "$PROJECT_ROOT/scripts/release/normalize-macos-python-framework.sh" "$PYTHON_FRAMEWORK"
fi

ACTIVE_ENGINE_ENTITLEMENTS="$ENGINE_ENTITLEMENTS"
if [[ "$ADHOC" == true ]]; then
  ACTIVE_ENGINE_ENTITLEMENTS="$LOCAL_ENGINE_ENTITLEMENTS"
fi

sign_code() {
  local code_path="$1"
  shift
  if [[ "$ADHOC" == true ]]; then
    codesign --force --sign "$IDENTITY" --options runtime --timestamp=none "$@" "$code_path"
  else
    codesign --force --sign "$SIGNING_IDENTITY" --options runtime --timestamp "$@" "$code_path"
  fi
}

# Apple requires manual distribution signing from the inside out. Sign every
# embedded Mach-O independently, then its framework wrapper, the audio-owning
# engine executable, the native supervisor, and finally the application.
while IFS= read -r -d '' code_path; do
  if [[ "$code_path" == "$ENGINE" || "$code_path" == "$SUPERVISOR" || "$code_path" == "$PYTHON_FRAMEWORK/"* ]]; then
    continue
  fi
  case "$(file -b "$code_path")" in
    Mach-O*) sign_code "$code_path" ;;
  esac
done < <(find "$APP_PATH/Contents" -type f -print0)

if [[ -d "$PYTHON_FRAMEWORK" ]]; then
  sign_code "$PYTHON_FRAMEWORK"
  codesign --verify --strict --verbose=2 "$PYTHON_FRAMEWORK"
  codesign --verify --strict --verbose=2 "$PYTHON_FRAMEWORK/Versions/Current/Python"
fi
sign_code "$ENGINE" --entitlements "$ACTIVE_ENGINE_ENTITLEMENTS"
sign_code "$SUPERVISOR" --entitlements "$SUPERVISOR_ENTITLEMENTS"
sign_code "$APP_PATH" --entitlements "$SUPERVISOR_ENTITLEMENTS"

"$PROJECT_ROOT/scripts/release/check-macos-app-bundle.sh" "$APP_PATH"
ENGINE_SIGNING="$(codesign -d --entitlements :- "$ENGINE" 2>&1)"
SUPERVISOR_SIGNING="$(codesign -d --entitlements :- "$SUPERVISOR" 2>&1)"
APP_SIGNING="$(codesign -d --entitlements :- "$APP_PATH" 2>&1)"
if [[ "$ENGINE_SIGNING" != *"com.apple.security.device.audio-input"* ]]; then
  echo "The audio engine signature is missing its audio-input entitlement." >&2
  exit 1
fi
if [[ "$SUPERVISOR_SIGNING" != *"com.apple.security.device.audio-input"* || "$APP_SIGNING" != *"com.apple.security.device.audio-input"* ]]; then
  echo "The responsible app signature is missing its audio-input entitlement." >&2
  exit 1
fi
if [[ "$ENGINE_SIGNING" != *"com.apple.security.cs.allow-unsigned-executable-memory"* ]]; then
  echo "The engine signature cannot support the optional OpenAI Whisper Numba runtime." >&2
  exit 1
fi
if [[ "$ENGINE_SIGNING" == *"com.apple.security.get-task-allow"* || "$SUPERVISOR_SIGNING" == *"com.apple.security.get-task-allow"* || "$APP_SIGNING" == *"com.apple.security.get-task-allow"* ]]; then
  echo "A shipping executable unexpectedly contains get-task-allow." >&2
  exit 1
fi
if [[ "$ENGINE_SIGNING" == *"com.apple.security.cs.disable-executable-page-protection"* || "$SUPERVISOR_SIGNING" == *"com.apple.security.cs.disable-executable-page-protection"* || "$APP_SIGNING" == *"com.apple.security.cs.disable-executable-page-protection"* ]]; then
  echo "A shipping executable unexpectedly disables executable page protection." >&2
  exit 1
fi
if [[ "$ADHOC" == false && "$ENGINE_SIGNING" == *"com.apple.security.cs.disable-library-validation"* ]]; then
  echo "Production engine signing unexpectedly disables library validation." >&2
  exit 1
fi

if [[ "$ADHOC" == false ]]; then
  APP_SIGNATURE_DETAILS="$(codesign -d --verbose=4 "$APP_PATH" 2>&1)"
  if [[ "$APP_SIGNATURE_DETAILS" != *"Authority=$IDENTITY"* ]]; then
    echo "The application was not signed by the requested Developer ID identity." >&2
    exit 1
  fi
  if [[ "$APP_SIGNATURE_DETAILS" == *"TeamIdentifier=not set"* || "$APP_SIGNATURE_DETAILS" != *"TeamIdentifier="* ]]; then
    echo "The Developer ID signature has no Apple Team ID." >&2
    exit 1
  fi
  if [[ "$APP_SIGNATURE_DETAILS" != *"Timestamp="* ]]; then
    echo "The Developer ID signature has no secure timestamp." >&2
    exit 1
  fi
  echo "Developer ID, secure timestamp, and Hardened Runtime signing verified: $APP_PATH"
  echo "Gatekeeper assessment is intentionally deferred until Apple notarization and stapling are complete."
else
  echo "Local Hardened Runtime signing structure verified: $APP_PATH"
  echo "The local engine disables library validation only because ad-hoc code has no shared Team ID; its Numba exception is engine-only."
  echo "This ad-hoc bundle is not suitable for distribution or notarization."
fi

#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_PATH="${1:-}"
PRIVATE_KEY_PATH="${CHURCH_CAP_UPDATER_PRIVATE_KEY_PATH:-}"
KEYCHAIN_SERVICE="${CHURCH_CAP_UPDATER_KEYCHAIN_SERVICE:-Church Cap Tauri Updater Signing Key}"
KEYCHAIN_ACCOUNT="${CHURCH_CAP_UPDATER_KEYCHAIN_ACCOUNT:-$(id -un)}"

fail() {
  echo "error: $*" >&2
  exit 1
}

if [[ -z "$ARTIFACT_PATH" || ! -f "$ARTIFACT_PATH" ]]; then
  fail "usage: sign-updater-artifact.sh <existing updater artifact>"
fi
if [[ -z "$PRIVATE_KEY_PATH" || ! -f "$PRIVATE_KEY_PATH" ]]; then
  fail "set CHURCH_CAP_UPDATER_PRIVATE_KEY_PATH to the protected Tauri updater private key"
fi
if [[ "$(stat -f '%Lp' "$PRIVATE_KEY_PATH")" != "600" ]]; then
  fail "the updater private key must have permissions 600"
fi

KEY_PASSWORD="${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-}"
if [[ -z "$KEY_PASSWORD" ]]; then
  KEY_PASSWORD="$(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null)" || \
    fail "the updater key password is not available in the configured macOS Keychain item"
fi

TAURI_SIGNING_PRIVATE_KEY_PATH="$PRIVATE_KEY_PATH" \
TAURI_SIGNING_PRIVATE_KEY_PASSWORD="$KEY_PASSWORD" \
  "$PROJECT_ROOT/desktop/node_modules/.bin/tauri" signer sign "$ARTIFACT_PATH"

SIGNATURE_PATH="$ARTIFACT_PATH.sig"
if [[ ! -s "$SIGNATURE_PATH" ]]; then
  fail "Tauri did not create the expected signature: $SIGNATURE_PATH"
fi
echo "Signed updater artifact: $ARTIFACT_PATH"
echo "Signature: $SIGNATURE_PATH"

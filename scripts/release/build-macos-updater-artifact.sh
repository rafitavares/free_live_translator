#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_PATH="${1:-$PROJECT_ROOT/dist/macos-arm64/Church Cap.app}"

fail() {
  echo "error: $*" >&2
  exit 1
}

if [[ ! -d "$APP_PATH" || ! -f "$APP_PATH/Contents/Info.plist" ]]; then
  fail "signed Church Cap application not found: $APP_PATH"
fi
VERSION="$(plutil -extract CFBundleShortVersionString raw -o - "$APP_PATH/Contents/Info.plist")"
OUTPUT_PATH="${CHURCH_CAP_MACOS_UPDATER_ARTIFACT:-$PROJECT_ROOT/dist/Church-Cap-v$VERSION-macOS-Apple-Silicon.app.tar.gz}"
if [[ -e "$OUTPUT_PATH" || -e "$OUTPUT_PATH.sig" ]]; then
  fail "refusing to overwrite an existing updater artifact or signature"
fi

"$PROJECT_ROOT/scripts/release/check-macos-app-bundle.sh" "$APP_PATH"
SIGNING_DETAILS="$(codesign -d --verbose=4 "$APP_PATH" 2>&1)"
if [[ "$SIGNING_DETAILS" != *"Authority=Developer ID Application:"* ]]; then
  fail "the updater archive must contain a Developer ID application, not an ad-hoc build"
fi
if [[ "$SIGNING_DETAILS" == *"TeamIdentifier=not set"* || "$SIGNING_DETAILS" != *"TeamIdentifier="* ]]; then
  fail "the signed application has no Apple Team ID"
fi
xcrun stapler validate "$APP_PATH"

ARCHIVE_DIRECTORY="$(mktemp -d "${TMPDIR:-/private/tmp}/church-cap-updater.XXXXXX")"
cleanup() {
  rm -rf "$ARCHIVE_DIRECTORY"
}
trap cleanup EXIT

ditto "$APP_PATH" "$ARCHIVE_DIRECTORY/Church Cap.app"
COPYFILE_DISABLE=1 tar -czf "$OUTPUT_PATH" -C "$ARCHIVE_DIRECTORY" "Church Cap.app"
if ! tar -tzf "$OUTPUT_PATH" | head -1 | grep -Fqx "Church Cap.app/"; then
  fail "the updater archive does not have the required Church Cap.app root"
fi

"$PROJECT_ROOT/scripts/release/sign-updater-artifact.sh" "$OUTPUT_PATH"
echo "Production macOS updater artifact created: $OUTPUT_PATH"

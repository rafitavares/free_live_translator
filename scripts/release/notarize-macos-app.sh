#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$PROJECT_ROOT/scripts/release/macos-signing-identity.sh"
APP_PATH="${1:-$PROJECT_ROOT/dist/macos-arm64/Church Cap.app}"
IDENTITY="${CHURCH_CAP_CODESIGN_IDENTITY:-}"
IDENTITY_SHA1="${CHURCH_CAP_CODESIGN_IDENTITY_SHA1:-}"
NOTARY_PROFILE="${CHURCH_CAP_NOTARY_PROFILE:-}"
LOG_DIR="${CHURCH_CAP_NOTARY_LOG_DIR:-$PROJECT_ROOT/dist/notarization}"

fail() {
  echo "error: $*" >&2
  exit 1
}

if [[ ! -d "$APP_PATH" || ! -f "$APP_PATH/Contents/Info.plist" ]]; then
  fail "macOS application not found: $APP_PATH"
fi
church_cap_resolve_developer_id "$IDENTITY" "$IDENTITY_SHA1" || exit 1
if [[ -z "$NOTARY_PROFILE" ]]; then
  fail "set CHURCH_CAP_NOTARY_PROFILE to a notarytool keychain profile"
fi

"$PROJECT_ROOT/scripts/release/check-macos-app-bundle.sh" "$APP_PATH"
SIGNING_DETAILS="$(codesign -d --verbose=4 "$APP_PATH" 2>&1)"
if [[ "$SIGNING_DETAILS" != *"Authority=$IDENTITY"* ]]; then
  fail "the application is not signed by the requested Developer ID identity"
fi
if [[ "$SIGNING_DETAILS" == *"TeamIdentifier=not set"* || "$SIGNING_DETAILS" != *"TeamIdentifier="* ]]; then
  fail "the Developer ID application has no Apple Team ID"
fi
if [[ "$SIGNING_DETAILS" != *"Timestamp="* ]]; then
  fail "the Developer ID application has no secure timestamp"
fi

# Validate credentials before creating the submission archive so an expired
# app-specific password or incorrect profile fails without changing the app.
xcrun notarytool history --keychain-profile "$NOTARY_PROFILE" >/dev/null

WORK_DIR="$(mktemp -d "${TMPDIR:-/private/tmp}/church-cap-app-notary.XXXXXX")"
RESULT_JSON="$WORK_DIR/submission.json"
APP_ARCHIVE="$WORK_DIR/Church-Cap.app.zip"
cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# notarytool accepts a ZIP containing an app, but not a bare .app directory.
# ditto preserves the bundle metadata and resource forks Apple expects.
ditto -c -k --keepParent "$APP_PATH" "$APP_ARCHIVE"

xcrun notarytool submit "$APP_ARCHIVE" \
  --keychain-profile "$NOTARY_PROFILE" \
  --wait \
  --output-format json >"$RESULT_JSON"

SUBMISSION_ID="$(plutil -extract id raw -o - "$RESULT_JSON")"
STATUS="$(plutil -extract status raw -o - "$RESULT_JSON")"
mkdir -p "$LOG_DIR"
cp "$RESULT_JSON" "$LOG_DIR/$SUBMISSION_ID-app-submission.json"
xcrun notarytool log "$SUBMISSION_ID" \
  --keychain-profile "$NOTARY_PROFILE" \
  "$LOG_DIR/$SUBMISSION_ID-app-log.json"

if [[ "$STATUS" != "Accepted" ]]; then
  fail "Apple app notarization status was $STATUS; inspect $LOG_DIR/$SUBMISSION_ID-app-log.json"
fi

xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
spctl --assess --type execute --verbose=4 "$APP_PATH"

echo "Developer ID app notarization, stapling, and Gatekeeper assessment passed: $APP_PATH"
echo "Notarization evidence: $LOG_DIR/$SUBMISSION_ID-app-log.json"

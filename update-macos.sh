#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
export CHURCH_CAP_UPDATE_APP_DIR="$APP_DIR"
exec /usr/bin/env bash "$APP_DIR/scripts/update-unix.sh" "$@"

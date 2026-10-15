#!/usr/bin/env bash
set -euo pipefail

PYTHON_FRAMEWORK="${1:-}"

fail() {
  echo "error: $*" >&2
  exit 1
}

if [[ ! -d "$PYTHON_FRAMEWORK" || "$(basename "$PYTHON_FRAMEWORK")" != "Python.framework" ]]; then
  fail "usage: normalize-macos-python-framework.sh <Python.framework>"
fi

VERSION_DIRECTORY=""
VERSION_COUNT=0
for candidate in "$PYTHON_FRAMEWORK"/Versions/*; do
  if [[ -d "$candidate" && ! -L "$candidate" ]]; then
    VERSION_DIRECTORY="$candidate"
    VERSION_COUNT=$((VERSION_COUNT + 1))
  fi
done
if (( VERSION_COUNT != 1 )); then
  fail "expected exactly one concrete Python.framework version directory; found $VERSION_COUNT"
fi

VERSION_NAME="$(basename "$VERSION_DIRECTORY")"
if [[ ! -f "$VERSION_DIRECTORY/Python" || ! -d "$VERSION_DIRECTORY/Resources" ]]; then
  fail "Python.framework version $VERSION_NAME is incomplete"
fi

# Tauri's resource bundler currently materializes framework symlinks as copies.
# Restore Apple's canonical versioned framework layout before any distribution
# signing. The concrete version content remains untouched.
rm -rf \
  "$PYTHON_FRAMEWORK/_CodeSignature" \
  "$VERSION_DIRECTORY/_CodeSignature" \
  "$PYTHON_FRAMEWORK/Python" \
  "$PYTHON_FRAMEWORK/Resources" \
  "$PYTHON_FRAMEWORK/Versions/Current"
ln -s "$VERSION_NAME" "$PYTHON_FRAMEWORK/Versions/Current"
ln -s "Versions/Current/Python" "$PYTHON_FRAMEWORK/Python"
ln -s "Versions/Current/Resources" "$PYTHON_FRAMEWORK/Resources"

[[ "$(readlink "$PYTHON_FRAMEWORK/Versions/Current")" == "$VERSION_NAME" ]]
[[ "$(readlink "$PYTHON_FRAMEWORK/Python")" == "Versions/Current/Python" ]]
[[ "$(readlink "$PYTHON_FRAMEWORK/Resources")" == "Versions/Current/Resources" ]]
echo "Canonical Python.framework symlink layout restored: $PYTHON_FRAMEWORK"

#!/usr/bin/env bash

# Resolve a Developer ID Application identity without weakening authority
# verification. Apple may install multiple certificates with the same display
# name; codesign then requires the certificate's SHA-1 fingerprint.
church_cap_resolve_developer_id() {
  local requested_name="${1:-}"
  local requested_sha1="${2:-}"
  local identities=""
  local name_matches=""
  local normalized_sha1=""
  local selected_match=""

  if [[ "$requested_name" != Developer\ ID\ Application:* ]]; then
    echo "error: CHURCH_CAP_CODESIGN_IDENTITY must name a Developer ID Application identity" >&2
    return 1
  fi
  if ! identities="$(security find-identity -v -p codesigning)"; then
    echo "error: unable to inspect code-signing identities in the keychain" >&2
    return 1
  fi
  name_matches="$(printf '%s\n' "$identities" | grep -F "\"$requested_name\"" || true)"
  if [[ -z "$name_matches" ]]; then
    echo "error: the requested Developer ID Application identity is not available in the keychain" >&2
    return 1
  fi

  CHURCH_CAP_RESOLVED_CODESIGN_IDENTITY="$requested_name"
  if [[ -n "$requested_sha1" ]]; then
    if [[ ! "$requested_sha1" =~ ^[[:xdigit:]]{40}$ ]]; then
      echo "error: CHURCH_CAP_CODESIGN_IDENTITY_SHA1 must be the certificate's 40-character SHA-1 fingerprint" >&2
      return 1
    fi
    normalized_sha1="$(printf '%s' "$requested_sha1" | tr '[:lower:]' '[:upper:]')"
    selected_match="$(printf '%s\n' "$name_matches" | grep -Fi "$normalized_sha1" || true)"
    if [[ -z "$selected_match" ]]; then
      echo "error: CHURCH_CAP_CODESIGN_IDENTITY_SHA1 does not identify the requested Developer ID certificate" >&2
      return 1
    fi
    CHURCH_CAP_RESOLVED_CODESIGN_IDENTITY="$normalized_sha1"
  fi
}

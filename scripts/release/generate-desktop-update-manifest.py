#!/usr/bin/env python3
"""Create one platform's signed Tauri update-channel manifest."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_TARGETS = {"darwin-aarch64", "windows-x86_64"}
VERSION_PATTERN = re.compile(r"^(?:v)?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")
RELEASE_URL_PREFIX = "/Church-Cap/Live-Church-Captions/releases/download/"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Generate updates/desktop/<target>/latest.json for a signed Church Cap release."
    )
    result.add_argument("--version", required=True, help="Semantic application version, for example 0.8.1")
    result.add_argument("--target", required=True, choices=sorted(ALLOWED_TARGETS))
    result.add_argument("--artifact-url", required=True, help="HTTPS GitHub Release URL for the updater artifact")
    result.add_argument("--signature-file", required=True, type=Path, help="Tauri-generated .sig file")
    result.add_argument("--notes-file", type=Path, help="Plain-text release notes")
    result.add_argument("--published-at", help="RFC 3339 timestamp; defaults to the current UTC time")
    result.add_argument("--output-root", type=Path, default=Path("updates/desktop"))
    return result


def validated_version(value: str) -> str:
    match = VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError("version must be valid semantic version text")
    return value.strip().removeprefix("v")


def validated_release_url(value: str, version: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        raise ValueError("artifact URL must use https://github.com")
    if not parsed.path.startswith(RELEASE_URL_PREFIX):
        raise ValueError("artifact URL must belong to the Church Cap GitHub Releases download path")
    release_path = parsed.path.removeprefix(RELEASE_URL_PREFIX)
    tag, separator, asset_name = release_path.partition("/")
    if tag != f"v{version}":
        raise ValueError(f"artifact URL must use the unified v{version} release tag")
    if not separator or not asset_name or "/" in asset_name:
        raise ValueError("artifact URL must name one GitHub Release asset")
    if parsed.query or parsed.fragment:
        raise ValueError("artifact URL must not contain a query or fragment")
    return value


def validated_timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    candidate = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError("published-at must include a timezone")
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def read_signature(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"signature file does not exist: {path}")
    signature = path.read_text(encoding="utf-8").strip()
    if not signature or any(character.isspace() for character in signature):
        raise ValueError("signature file must contain one non-empty Tauri signature")
    return signature


def main() -> int:
    args = parser().parse_args()
    try:
        version = validated_version(args.version)
        artifact_url = validated_release_url(args.artifact_url, version)
        published_at = validated_timestamp(args.published_at)
        signature = read_signature(args.signature_file)
    except (OSError, UnicodeError, ValueError) as error:
        parser().error(str(error))

    notes = ""
    if args.notes_file:
        try:
            notes = args.notes_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as error:
            parser().error(f"release notes could not be read: {error}")

    manifest = {
        "version": version,
        "notes": notes,
        "pub_date": published_at,
        "url": artifact_url,
        "signature": signature,
    }
    output = args.output_root / args.target / "latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

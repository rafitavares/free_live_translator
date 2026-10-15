#!/usr/bin/env python3
"""Install Church Cap's reviewed optional spoken-language packs.

The archives are pinned to exact official Sherpa-ONNX release assets and
verified before extraction. Voice text and generated audio are never handled
by this installer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.paths import app_support_dir  # noqa: E402
from app.install_progress import write_install_progress  # noqa: E402
from app.tts_catalog import (  # noqa: E402
    ALL_VOICE_PACKAGE_IDS,
    RETIRED_VOICE_SOURCE_URLS,
    VOICE_PACKAGES,
    normalise_voice_package_selection,
)


MAX_ARCHIVE_FILES = 2500
MAX_EXPANDED_BYTES = 900 * 1024 * 1024
USER_AGENT = "Church-Cap/0.7.6 translated-audio-installer"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive_path, "r:bz2") as archive:
        members = archive.getmembers()
        if len(members) > MAX_ARCHIVE_FILES:
            raise RuntimeError("The voice archive contains too many files.")
        expanded = sum(max(0, member.size) for member in members if member.isfile())
        if expanded > MAX_EXPANDED_BYTES:
            raise RuntimeError("The voice archive expands beyond Church Cap's safety limit.")
        checked: list[tuple[tarfile.TarInfo, Path]] = []
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise RuntimeError("The voice archive contains an unsafe path.")
            if not (member.isdir() or member.isfile()):
                raise RuntimeError("The voice archive contains an unsupported link or device entry.")
            target = (destination / Path(*name.parts)).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise RuntimeError("The voice archive escapes the TTS folder.") from exc
            checked.append((member, target))
        for member, target in checked:
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError("The voice archive contains an unreadable file.")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def download(url: str, destination: Path, *, on_progress=None) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or not parsed.path.startswith("/k2-fsa/sherpa-onnx/releases/download/tts-models/"):
        raise RuntimeError("The voice download URL is not an approved Church Cap source.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    # The URL is fixed to the approved HTTPS release path above and the
    # complete archive is SHA-256 verified before Church Cap extracts it.
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:  # nosec B310
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if on_progress is not None:
                on_progress(downloaded)


def install_package(
    package_id: str,
    package: dict,
    root: Path,
    archive_dir: Path | None,
    force: bool,
    *,
    item_index: int,
    item_count: int,
    completed_bytes: int,
    total_bytes: int,
    progress_items: list[dict],
) -> None:
    package_label = str(package["label"])
    package_bytes = max(1, int(package["download_bytes"]))

    def report(fraction: float, state: str, phase: str, detail: str, downloaded: int = 0) -> None:
        package_percent = max(0, min(100, round(fraction * 100)))
        progress_items[item_index - 1].update(state=state, percent=package_percent)
        weighted = completed_bytes + (package_bytes * max(0.0, min(1.0, fraction)))
        overall = 8 + round(90 * (weighted / max(1, total_bytes)))
        write_install_progress(
            overall,
            phase,
            detail,
            downloaded_bytes=min(total_bytes, completed_bytes + max(0, downloaded)),
            total_bytes=total_bytes,
            item_index=item_index,
            item_count=item_count,
            items=progress_items,
        )

    voices_root = root / "voices"
    target = voices_root / str(package["folder"])
    required = []
    for entry in package["entries"]:
        for field in ("model", "tokens"):
            relative = Path(str(entry[field]))
            try:
                relative.relative_to("voices")
            except ValueError as exc:
                raise RuntimeError("The reviewed voice catalogue contains an invalid resource path.") from exc
            required.append(root / relative)
    if not force and all(path.exists() for path in required):
        print(f"Voice resources already installed: {package['folder']}")
        report(1.0, "complete", "package-complete", f"{package_label} is already installed.", package_bytes)
        return

    voices_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="church-cap-tts-", dir=root) as temporary:
        temporary_path = Path(temporary)
        archive_path = temporary_path / str(package["archive"])
        cached = archive_dir / str(package["archive"]) if archive_dir else None
        if cached and cached.exists():
            report(0.68, "downloading", "copying", f"Using the verified local {package_label} archive.", package_bytes)
            shutil.copy2(cached, archive_path)
        else:
            print(f"Downloading {package['archive']}…")
            last_percent = -1

            def download_progress(downloaded: int) -> None:
                nonlocal last_percent
                ratio = min(1.0, downloaded / package_bytes)
                current_percent = int(ratio * 100)
                if current_percent == last_percent and downloaded < package_bytes:
                    return
                last_percent = current_percent
                report(
                    ratio * 0.70,
                    "downloading",
                    "downloading",
                    f"Downloading {package_label}.",
                    downloaded,
                )

            report(0.0, "downloading", "downloading", f"Starting {package_label} download.")
            download(str(package["url"]), archive_path, on_progress=download_progress)
        report(0.76, "verifying", "verifying", f"Verifying {package_label}.", package_bytes)
        actual = sha256(archive_path)
        if actual != package["sha256"]:
            raise RuntimeError(f"Checksum verification failed for {package['archive']}.")
        extracted = temporary_path / "extracted"
        extracted.mkdir()
        report(0.84, "extracting", "extracting", f"Extracting {package_label}.", package_bytes)
        safe_extract(archive_path, extracted)
        source = extracted / str(package["folder"])
        if not source.is_dir():
            raise RuntimeError(f"Expected folder missing from {package['archive']}.")
        if target.exists():
            shutil.rmtree(target)
        report(0.95, "installing", "installing", f"Installing {package_label}.", package_bytes)
        shutil.move(str(source), str(target))
        print(f"Installed and verified: {package['folder']}")
        report(1.0, "complete", "package-complete", f"{package_label} is ready.", package_bytes)


def write_manifest(root: Path, requested_packages: tuple[str, ...]) -> Path:
    manifest_path = root / "voices.json"
    existing: dict = {"schema_version": 1, "voices": []}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if int(existing.get("schema_version", 0)) != 1 or not isinstance(existing.get("voices"), list):
            raise RuntimeError("The existing voices.json is not a supported Church Cap voice manifest.")

    replacements = [
        entry
        for package_id in requested_packages
        for entry in VOICE_PACKAGES[package_id]["entries"]
    ]
    replacement_languages = {entry["language"] for entry in replacements}
    retained = [
        entry for entry in existing["voices"]
        if (
            isinstance(entry, dict)
            and entry.get("language") not in replacement_languages
            and entry.get("source_url") not in RETIRED_VOICE_SOURCE_URLS
        )
    ]
    payload = {
        "schema_version": 1,
        "description": "Church Cap reviewed local translated-audio voices. Generated audio remains local and in memory.",
        "voices": retained + replacements,
    }
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    return manifest_path


def write_voice_notices(root: Path) -> Path:
    source = PROJECT_ROOT / "docs" / "legal" / "SPOKEN_LANGUAGE_MODELS.md"
    if not source.is_file():
        raise RuntimeError("The spoken-language model notices are missing from this Church Cap release.")
    destination = root / "VOICE_NOTICES.md"
    temporary = destination.with_suffix(".md.tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)
    return destination


def parse_packages(value: str) -> tuple[str, ...]:
    return normalise_voice_package_selection(value.split(","))


def parse_languages(value: str) -> tuple[str, ...]:
    """Retain the v0.7.5 manual language flag while mapping to package IDs."""
    aliases = {"zh-hans": "zh", "zh-hant": "zh", "chinese": "zh"}
    selected: list[str] = []
    for item in value.split(","):
        code = item.strip().lower()
        package_id = aliases.get(code, code)
        if package_id and package_id not in selected:
            selected.append(package_id)
    try:
        return normalise_voice_package_selection(selected)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Install verified optional Church Cap spoken-language packs.")
    parser.add_argument("--packages", type=parse_packages, help=f"Comma-separated package IDs: {', '.join(ALL_VOICE_PACKAGE_IDS)}")
    parser.add_argument("--languages", type=parse_languages, help="Backward-compatible comma-separated caption-language codes.")
    parser.add_argument("--tts-root", type=Path, help="Override the Church Cap TTS data folder (mainly for tests).")
    parser.add_argument("--archive-dir", type=Path, help="Use already-downloaded verified archives from this folder.")
    parser.add_argument("--force", action="store_true", help="Reinstall resources even when they already exist.")
    args = parser.parse_args()
    if args.packages and args.languages:
        parser.error("Use either --packages or --languages, not both.")
    requested = args.packages or args.languages or ALL_VOICE_PACKAGE_IDS

    root = (args.tts_root or (app_support_dir() / "tts")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    progress_items = [
        {"id": package_id, "label": str(VOICE_PACKAGES[package_id]["label"]), "state": "pending", "percent": 0}
        for package_id in requested
    ]
    total_bytes = sum(int(VOICE_PACKAGES[package_id]["download_bytes"]) for package_id in requested)
    completed_bytes = 0
    write_install_progress(
        8,
        "preparing-voices",
        f"Preparing {len(requested)} selected spoken-language pack{'s' if len(requested) != 1 else ''}.",
        total_bytes=total_bytes,
        item_count=len(requested),
        items=progress_items,
    )
    for index, package_id in enumerate(requested, start=1):
        install_package(
            package_id,
            VOICE_PACKAGES[package_id],
            root,
            args.archive_dir,
            args.force,
            item_index=index,
            item_count=len(requested),
            completed_bytes=completed_bytes,
            total_bytes=total_bytes,
            progress_items=progress_items,
        )
        completed_bytes += int(VOICE_PACKAGES[package_id]["download_bytes"])
    write_install_progress(
        99,
        "finalising",
        "Writing the local voice manifest and licence notices.",
        downloaded_bytes=total_bytes,
        total_bytes=total_bytes,
        item_index=len(requested),
        item_count=len(requested),
        items=progress_items,
    )
    manifest = write_manifest(root, requested)
    notices = write_voice_notices(root)
    print(f"Voice manifest ready: {manifest}")
    print(f"Voice notices ready: {notices}")
    print("Restart Church Cap, select a translated language, and press Listen.")
    if "zh" in requested:
        print("Note: the Traditional Chinese voice speaks Mandarin, not Cantonese.")
    write_install_progress(
        100,
        "complete",
        "All selected spoken-language packs are ready.",
        downloaded_bytes=total_bytes,
        total_bytes=total_bytes,
        item_index=len(requested),
        item_count=len(requested),
        items=progress_items,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

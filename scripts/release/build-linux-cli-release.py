"""Build the deterministic, curated Church Cap Linux CLI archive."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import tarfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "packaging" / "linux" / "release-manifest.txt"
DEFAULT_OUTPUT = ROOT / "dist" / "releases" / "Church-Cap-Linux-CLI.tar.gz"
ARCHIVE_ROOT = PurePosixPath("Church-Cap-Linux-CLI")
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
SKIP_NAMES = {".DS_Store"}
EXECUTABLE_SUFFIXES = {".sh"}


def manifest_paths(path: Path) -> list[Path]:
    entries: list[Path] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        candidate = (ROOT / value).resolve()
        if ROOT not in candidate.parents and candidate != ROOT:
            raise RuntimeError(f"Manifest path leaves the project: {value}")
        if not candidate.exists():
            raise FileNotFoundError(f"Manifest path is missing: {value}")
        entries.append(candidate)
    return entries


def included_files(entries: list[Path]) -> list[Path]:
    selected: set[Path] = set()
    for entry in entries:
        candidates = entry.rglob("*") if entry.is_dir() else (entry,)
        for candidate in candidates:
            relative = candidate.relative_to(ROOT)
            if not candidate.is_file() or SKIP_PARTS.intersection(relative.parts):
                continue
            if (
                candidate.suffix.casefold() in SKIP_SUFFIXES
                or candidate.name in SKIP_NAMES
                or candidate.name.startswith("._")
            ):
                continue
            selected.add(candidate)
    return sorted(selected, key=lambda item: item.relative_to(ROOT).as_posix())


def add_file(archive: tarfile.TarFile, source: Path) -> None:
    relative = PurePosixPath(source.relative_to(ROOT).as_posix())
    info = tarfile.TarInfo(str(ARCHIVE_ROOT / relative))
    payload = source.read_bytes()
    info.size = len(payload)
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    info.mode = 0o755 if source.suffix.casefold() in EXECUTABLE_SUFFIXES else 0o644
    archive.addfile(info, io.BytesIO(payload))


def build(destination: Path, manifest: Path) -> str:
    files = included_files(manifest_paths(manifest))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for source in files:
                    add_file(archive, source)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    checksum = destination.with_name(destination.name + ".sha256")
    checksum.write_text(f"{digest}  {destination.name}\n", encoding="ascii", newline="\n")
    print(f"Built {destination} ({len(files)} files)")
    print(f"SHA-256 {digest}")
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output.resolve(), args.manifest.resolve())


if __name__ == "__main__":
    main()

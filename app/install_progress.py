"""Small, privacy-safe progress contract shared by GUI-launched installers."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Iterable, Mapping


INSTALL_PROGRESS_ENV = "CHURCH_CAP_INSTALL_PROGRESS_FILE"
MAX_PROGRESS_FILE_BYTES = 256 * 1024
_ITEM_STATES = {"pending", "downloading", "verifying", "extracting", "installing", "complete", "error"}
_WINDOWS_REPLACE_RETRY_SECONDS = (0.02, 0.05, 0.1)


def progress_path_from_environment() -> Path | None:
    value = os.environ.get(INSTALL_PROGRESS_ENV, "").strip()
    return Path(value).expanduser().resolve() if value else None


def _bounded_percent(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _nonnegative_int(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _clean_text(value: object, *, maximum: int = 160) -> str:
    return " ".join(str(value or "").split())[:maximum]


def _normalise_items(items: Iterable[Mapping[str, object]] | None) -> list[dict]:
    result: list[dict] = []
    for raw in list(items or ())[:64]:
        item_id = _clean_text(raw.get("id"), maximum=48)
        if not item_id:
            continue
        state = _clean_text(raw.get("state"), maximum=24).casefold()
        result.append(
            {
                "id": item_id,
                "label": _clean_text(raw.get("label"), maximum=80) or item_id,
                "state": state if state in _ITEM_STATES else "pending",
                "percent": _bounded_percent(raw.get("percent")),
            }
        )
    return result


def write_install_progress(
    percent: object,
    phase: object,
    detail: object = "",
    *,
    path: Path | None = None,
    downloaded_bytes: object = 0,
    total_bytes: object = 0,
    item_index: object = 0,
    item_count: object = 0,
    items: Iterable[Mapping[str, object]] | None = None,
    indeterminate: bool = False,
) -> dict:
    destination = path or progress_path_from_environment()
    previous = read_install_progress(destination) if destination is not None and items is None else None
    payload = {
        "percent": _bounded_percent(percent),
        "phase": _clean_text(phase, maximum=48) or "preparing",
        "detail": _clean_text(detail),
        "downloaded_bytes": _nonnegative_int(downloaded_bytes),
        "total_bytes": _nonnegative_int(total_bytes),
        "item_index": _nonnegative_int(item_index),
        "item_count": _nonnegative_int(item_count),
        "items": _normalise_items(items if items is not None else (previous or {}).get("items")),
        "indeterminate": bool(indeterminate),
        "updated_at": time.time(),
    }
    if destination is None:
        return payload
    # Progress is optional telemetry. A locked progress file must never abort a
    # model download, particularly on Windows where antivirus/indexing software
    # can briefly deny replacement of a JSON file that another process reads.
    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))

        replaced = False
        for attempt in range(len(_WINDOWS_REPLACE_RETRY_SECONDS) + 1):
            try:
                os.replace(temporary, destination)
                replaced = True
                break
            except PermissionError:
                if attempt >= len(_WINDOWS_REPLACE_RETRY_SECONDS):
                    break
                time.sleep(_WINDOWS_REPLACE_RETRY_SECONDS[attempt])

        if not replaced:
            # A non-atomic fallback is acceptable here: readers reject partial
            # JSON and retain their last known state, while the installer keeps
            # running instead of failing because a percentage could not update.
            destination.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
    return payload


def read_install_progress(path: Path) -> dict | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_PROGRESS_FILE_BYTES:
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    return {
        "percent": _bounded_percent(raw.get("percent")),
        "phase": _clean_text(raw.get("phase"), maximum=48) or "preparing",
        "detail": _clean_text(raw.get("detail")),
        "downloaded_bytes": _nonnegative_int(raw.get("downloaded_bytes")),
        "total_bytes": _nonnegative_int(raw.get("total_bytes")),
        "item_index": _nonnegative_int(raw.get("item_index")),
        "item_count": _nonnegative_int(raw.get("item_count")),
        "items": _normalise_items(raw.get("items") if isinstance(raw.get("items"), list) else ()),
        "indeterminate": bool(raw.get("indeterminate")),
    }


def clear_install_progress(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass

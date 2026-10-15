"""Resource and mutable-data locations for source and packaged runtimes."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2]


class RuntimeMode(StrEnum):
    SOURCE = "source"
    PACKAGED = "packaged"


def runtime_mode() -> RuntimeMode:
    configured = os.getenv("CHURCH_CAP_RUNTIME_MODE", "").strip().casefold()
    if configured:
        try:
            return RuntimeMode(configured)
        except ValueError as exc:
            raise ValueError("CHURCH_CAP_RUNTIME_MODE must be 'source' or 'packaged'.") from exc
    return RuntimeMode.PACKAGED if getattr(sys, "frozen", False) else RuntimeMode.SOURCE


def resource_root() -> Path:
    override = os.getenv("CHURCH_CAP_RESOURCE_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    frozen_root = getattr(sys, "_MEIPASS", None)
    if runtime_mode() is RuntimeMode.PACKAGED and frozen_root:
        return Path(frozen_root).resolve()
    return SOURCE_ROOT


def app_support_dir() -> Path:
    override = os.getenv("CHURCH_CAP_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Church Cap"
    if platform.system() == "Windows":
        base = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Church Cap"
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "church-cap"


@dataclass(frozen=True)
class RuntimePaths:
    mode: RuntimeMode
    resources: Path
    support: Path
    data: Path
    config: Path
    models: Path
    cache: Path
    logs: Path
    updates: Path
    recovery: Path
    exports: Path


def runtime_paths() -> RuntimePaths:
    mode = runtime_mode()
    support = app_support_dir()
    models = support / "models" if mode is RuntimeMode.PACKAGED else SOURCE_ROOT / "data" / "models"
    return RuntimePaths(
        mode=mode,
        resources=resource_root(),
        support=support,
        data=support / "data",
        config=support / "config",
        models=models,
        cache=support / "cache",
        logs=support / "logs",
        updates=support / "updates",
        recovery=support / "recovery",
        exports=support / "exports",
    )


def data_path(filename: str) -> Path:
    return runtime_paths().data / filename


def model_data_dir() -> Path:
    override = os.getenv("CHURCH_CAP_MODEL_DIR", "").strip()
    return Path(override).expanduser().resolve() if override else runtime_paths().models

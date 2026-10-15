"""Typed contracts for operations whose implementation differs by distribution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol


class PlatformFeature(StrEnum):
    APPLICATION_UPDATE = "application_update"
    RESOURCE_INSTALL = "resource_install"
    CUDA_RUNTIME_INSTALL = "cuda_runtime_install"
    PASSWORD_RESET = "password_reset"
    REVEAL_LOCAL_PATH = "reveal_local_path"


@dataclass(frozen=True)
class PlatformCapability:
    feature: PlatformFeature
    available: bool
    backend: str
    reason: str = ""

    def public_state(self) -> dict[str, str | bool]:
        return asdict(self)


class PlatformServiceAdapter(Protocol):
    """Narrow boundary used by application services, never directly by browser code."""

    @property
    def backend_name(self) -> str: ...

    def capability(self, feature: PlatformFeature) -> PlatformCapability: ...

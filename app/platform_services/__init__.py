"""Platform boundaries shared by source installs and signed desktop builds."""

from app.platform_services.contracts import (
    PlatformCapability,
    PlatformFeature,
    PlatformServiceAdapter,
)
from app.platform_services.paths import RuntimeMode, RuntimePaths, runtime_mode, runtime_paths

__all__ = [
    "PlatformCapability",
    "PlatformFeature",
    "PlatformServiceAdapter",
    "RuntimeMode",
    "RuntimePaths",
    "runtime_mode",
    "runtime_paths",
]

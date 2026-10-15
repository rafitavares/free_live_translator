"""Allow-listed platform capabilities for traditional source installations."""

from __future__ import annotations

import platform
from pathlib import Path

from app.platform_services.contracts import PlatformCapability, PlatformFeature


class SourcePlatformAdapter:
    backend_name = "source-scripts"

    def __init__(self, project_root: Path, *, system: str | None = None):
        self.project_root = Path(project_root).resolve()
        self.system = system or platform.system()

    def _script_for(self, feature: PlatformFeature) -> Path | None:
        suffix = "windows.ps1" if self.system == "Windows" else "macos.sh" if self.system == "Darwin" else "linux.sh"
        scripts = {
            PlatformFeature.APPLICATION_UPDATE: self.project_root / f"update-{suffix}",
            PlatformFeature.PASSWORD_RESET: self.project_root / ("reset-operator-password.ps1" if self.system == "Windows" else "reset-operator-password.sh"),
            PlatformFeature.CUDA_RUNTIME_INSTALL: (
                self.project_root / "scripts" / "install-cuda-runtime-windows.ps1"
                if self.system == "Windows"
                else self.project_root / "install-cuda-runtime-linux.sh"
                if self.system == "Linux"
                else None
            ),
        }
        return scripts.get(feature)

    def capability(self, feature: PlatformFeature) -> PlatformCapability:
        if feature in {PlatformFeature.RESOURCE_INSTALL, PlatformFeature.REVEAL_LOCAL_PATH}:
            return PlatformCapability(feature, True, self.backend_name)
        script = self._script_for(feature)
        if script is None:
            return PlatformCapability(feature, False, self.backend_name, "This operation is not supported on this platform.")
        if not script.is_file():
            return PlatformCapability(feature, False, self.backend_name, "The required source-install helper is missing.")
        return PlatformCapability(feature, True, self.backend_name)

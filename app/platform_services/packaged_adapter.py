"""Capability boundary for the future native desktop supervisor."""

from __future__ import annotations

from collections.abc import Iterable

from app.platform_services.contracts import PlatformCapability, PlatformFeature


class PackagedPlatformAdapter:
    backend_name = "desktop-supervisor-ipc"

    def __init__(self, advertised_features: Iterable[PlatformFeature] = ()):
        self._advertised_features = frozenset(advertised_features)

    def capability(self, feature: PlatformFeature) -> PlatformCapability:
        if feature in self._advertised_features:
            return PlatformCapability(feature, True, self.backend_name)
        return PlatformCapability(
            feature,
            False,
            self.backend_name,
            "The installed desktop supervisor does not advertise this capability.",
        )

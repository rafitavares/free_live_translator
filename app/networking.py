from __future__ import annotations

import os
import platform
import socket
import subprocess
from functools import lru_cache

from app.settings import get_settings


def local_ip() -> str:
    """Best-effort LAN IP address without sending traffic."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _run(cmd: list[str]) -> str | None:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


@lru_cache(maxsize=1)
def local_hostname_is_configured() -> bool:
    configured = (os.environ.get("CAPTION_LOCAL_HOSTNAME", "") or get_settings().caption_local_hostname or "").strip()
    if configured:
        return True
    return platform.system() == "Darwin" and bool(_run(["scutil", "--get", "LocalHostName"]))


@lru_cache(maxsize=1)
def detected_local_hostname() -> str:
    """Return an explicit or suggested friendly hostname for QR codes.

    On macOS, scutil LocalHostName maps to Bonjour/mDNS as <name>.local.
    Other platforms can show a safe <computer-name>.local candidate, but the UI
    labels it as requiring DNS/mDNS setup until explicitly configured.
    """
    configured = (os.environ.get("CAPTION_LOCAL_HOSTNAME", "") or get_settings().caption_local_hostname or "").strip()
    if configured:
        return configured[:-1] if configured.endswith(".") else configured

    local_host = _run(["scutil", "--get", "LocalHostName"]) if platform.system() == "Darwin" else None
    if local_host:
        return local_host if local_host.endswith(".local") else f"{local_host}.local"

    host = socket.gethostname().strip().split(".")[0]
    if host and host.lower() not in {"localhost", "local"}:
        safe = "".join(ch for ch in host if ch.isalnum() or ch == "-").strip("-")
        if safe:
            return f"{safe}.local"

    return local_ip()


def default_base_url(port: int, scheme: str = "http") -> str:
    return f"{scheme}://{detected_local_hostname()}:{port}"

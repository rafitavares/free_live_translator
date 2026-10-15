"""Collect the wheel-provided PortAudio runtime used on Windows and macOS."""

from PyInstaller.utils.hooks import collect_all


datas, binaries, hiddenimports = collect_all("_sounddevice_data")
hiddenimports += ["_cffi_backend"]

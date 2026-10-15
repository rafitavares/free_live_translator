# -*- mode: python ; coding: utf-8 -*-
"""Initial one-folder Church Cap engine specification for native builds."""

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules


ROOT = Path(SPECPATH).parents[1]

datas = [
    (str(ROOT / "app" / "templates"), "app/templates"),
    (str(ROOT / "app" / "static"), "app/static"),
    (str(ROOT / "app" / "locales"), "app/locales"),
    (str(ROOT / "app" / "resources"), "app/resources"),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "docs" / "legal"), "docs/legal"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "scripts" / "install-tts-voices.py"), "scripts"),
]
binaries = []
hiddenimports = collect_submodules("uvicorn")
hiddenimports += ["app.resource_installer", "app.windows_cuda_runtime"]

# These runtimes use dynamic imports and native libraries. Collect their
# package-owned data/binaries now; Phase 1 smoke tests will narrow or extend
# these hooks from evidence on each native target.
for package in (
    "whisper",
    "faster_whisper",
    "argostranslate",
    "opencc",
    "sherpa_onnx",
    "sounddevice",
    "transformers",
    "safetensors",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(ROOT / "engine" / "entrypoint.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT / "packaging" / "engine" / "hooks")],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="church-cap-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    # The Windows supervisor still needs the engine's stdout/stderr pipes for
    # versioned lifecycle events, but end users should not see a console window.
    # PyInstaller ignores no-console pipe semantics, so retain console=True and
    # ask the Windows bootloader to hide its console at the earliest stage.
    hide_console="hide-early" if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="church-cap-engine",
)

"""Generate an Explorer-compatible multi-size Windows installer icon."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "branding" / "church-cap-app-icon-white-glass.png"
DESTINATION = ROOT / "desktop" / "src-tauri" / "installer" / "windows" / "installer-icon.ico"
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def main() -> None:
    with Image.open(SOURCE) as source:
        icon = source.convert("RGBA")
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        # DIB/BMP-backed frames are intentionally used instead of PNG-backed
        # ICO frames. Explorer and NSIS resource tools reliably expose these
        # before setup starts, including on older supported Windows builds.
        icon.save(DESTINATION, format="ICO", sizes=[(size, size) for size in SIZES], bitmap_format="bmp")
    print(f"Generated Church Cap installer icon: {DESTINATION}")


if __name__ == "__main__":
    main()

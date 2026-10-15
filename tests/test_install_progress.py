import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.install_progress import clear_install_progress, read_install_progress, write_install_progress


class InstallerProgressContractTests(unittest.TestCase):
    def test_round_trip_clamps_values_and_preserves_safe_package_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.json"
            write_install_progress(
                42.6,
                "downloading",
                "Downloading Spanish voice",
                path=path,
                downloaded_bytes=25,
                total_bytes=100,
                item_index=1,
                item_count=2,
                items=[
                    {"id": "es", "label": "Spanish", "state": "downloading", "percent": 36},
                    {"id": "fr", "label": "French", "state": "pending", "percent": -5},
                ],
            )
            progress = read_install_progress(path)
            self.assertEqual(progress["percent"], 43)
            self.assertEqual(progress["downloaded_bytes"], 25)
            self.assertEqual(progress["items"][0]["state"], "downloading")
            self.assertEqual(progress["items"][1]["percent"], 0)
            write_install_progress(50, "dependencies", "Preparing runtime", path=path)
            self.assertEqual(len(read_install_progress(path)["items"]), 2)

    def test_malformed_progress_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.json"
            path.write_text("not json", encoding="utf-8")
            self.assertIsNone(read_install_progress(path))
            path.write_text(json.dumps({"percent": "not-a-number", "downloaded_bytes": "private/path"}), encoding="utf-8")
            progress = read_install_progress(path)
            self.assertEqual(progress["percent"], 0)
            self.assertEqual(progress["downloaded_bytes"], 0)

    def test_clear_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.json"
            write_install_progress(1, "preparing", path=path)
            clear_install_progress(path)
            clear_install_progress(path)
            self.assertFalse(path.exists())

    def test_windows_progress_file_lock_never_aborts_the_installer(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.json"
            with patch("app.install_progress.os.replace", side_effect=PermissionError("temporarily locked")), patch(
                "app.install_progress.time.sleep"
            ):
                payload = write_install_progress(37, "downloading", "Downloading voice", path=path)
            self.assertEqual(payload["percent"], 37)
            self.assertEqual(read_install_progress(path)["phase"], "downloading")
            self.assertEqual(list(Path(temporary).glob(".progress.json.*.tmp")), [])


class InstallerProgressSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = Path("app/main.py").read_text(encoding="utf-8")
        cls.operator = Path("app/templates/operator.html").read_text(encoding="utf-8")
        cls.styles = Path("app/static/styles.css").read_text(encoding="utf-8")
        cls.voice_installer = Path("scripts/install-tts-voices.py").read_text(encoding="utf-8")

    def test_gui_exposes_overall_translation_and_spoken_progress(self):
        self.assertIn('id="translationInstallProgressBar"', self.operator)
        self.assertIn('id="translationPackageProgress"', self.operator)
        self.assertIn('id="translatedAudioInstallProgressBar"', self.operator)
        self.assertIn('id="translatedAudioPackageProgress"', self.operator)
        self.assertIn("renderTranslationInstallProgress", self.operator)
        self.assertIn("installer-package-progress-ring", self.styles)

    def test_gui_installers_receive_private_progress_file_via_environment(self):
        self.assertGreaterEqual(self.main.count("INSTALL_PROGRESS_ENV"), 3)
        self.assertIn('process_environment["PYTHONUNBUFFERED"] = "1"', self.main)
        self.assertIn("read_install_progress", self.main)

    def test_voice_download_reports_real_chunk_progress_and_package_stages(self):
        self.assertIn("on_progress(downloaded)", self.voice_installer)
        for state in ("downloading", "verifying", "extracting", "installing", "complete"):
            self.assertIn(f'"{state}"', self.voice_installer)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release" / "generate-desktop-update-manifest.py"


class DesktopUpdateManifestTests(unittest.TestCase):
    def run_generator(self, temporary: Path, artifact_url: str) -> subprocess.CompletedProcess[str]:
        signature = temporary / "artifact.sig"
        signature.write_text("signed-payload", encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            "--version",
            "0.8.1",
            "--target",
            "darwin-aarch64",
            "--artifact-url",
            artifact_url,
            "--signature-file",
            str(signature),
            "--published-at",
            "2026-08-14T20:00:00Z",
            "--output-root",
            str(temporary / "updates"),
        ]
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def test_generates_one_independent_platform_channel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = self.run_generator(
                temporary,
                "https://github.com/Church-Cap/Live-Church-Captions/releases/download/v0.8.1/Church-Cap-v0.8.1-macOS-Apple-Silicon.app.tar.gz",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(
                (temporary / "updates" / "darwin-aarch64" / "latest.json").read_text()
            )
            self.assertEqual(manifest["version"], "0.8.1")
            self.assertEqual(manifest["signature"], "signed-payload")
            self.assertTrue(
                manifest["url"].startswith(
                    "https://github.com/Church-Cap/Live-Church-Captions/releases/download/v0.8.1/"
                )
            )

    def test_rejects_old_platform_prefixed_release_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_generator(
                Path(directory),
                "https://github.com/Church-Cap/Live-Church-Captions/releases/download/macos-v0.8.1/Church-Cap-v0.8.1-macOS-Apple-Silicon.app.tar.gz",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unified v0.8.1 release tag", result.stderr)

    def test_rejects_release_tag_that_does_not_match_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_generator(
                Path(directory),
                "https://github.com/Church-Cap/Live-Church-Captions/releases/download/v0.8.2/Church-Cap-v0.8.2-macOS-Apple-Silicon.app.tar.gz",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unified v0.8.1 release tag", result.stderr)

    def test_rejects_artifacts_outside_the_church_cap_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_generator(Path(directory), "https://example.com/untrusted.app.tar.gz")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("https://github.com", result.stderr)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from app.tts import uninstall_reviewed_voice_packages
from app.tts_catalog import (
    ALL_VOICE_CAPTION_LANGUAGES,
    ALL_VOICE_PACKAGE_IDS,
    RETIRED_VOICE_SOURCE_URLS,
    VOICE_PACKAGES,
    installed_reviewed_voice_package_ids,
    normalise_voice_package_selection,
    public_voice_catalog,
)


class SpokenLanguageCatalogTests(unittest.TestCase):
    def test_catalog_links_every_approved_caption_language_once(self):
        self.assertEqual(len(ALL_VOICE_CAPTION_LANGUAGES), len(set(ALL_VOICE_CAPTION_LANGUAGES)))
        self.assertEqual(
            set(ALL_VOICE_CAPTION_LANGUAGES),
            {"ca", "es", "fr", "kk", "lv", "ne", "nl", "sl", "sv", "uk", "zh-hans", "zh-hant"},
        )

    def test_every_package_is_checksum_pinned_and_has_bounded_size_metadata(self):
        total_download = 0
        total_installed = 0
        for package_id, package in VOICE_PACKAGES.items():
            self.assertEqual(package_id, package["id"])
            self.assertRegex(package["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(package["url"].startswith(
                "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/"
            ))
            self.assertGreater(package["download_bytes"], 1_000_000)
            self.assertGreaterEqual(package["installed_bytes_estimate"], package["download_bytes"])
            total_download += package["download_bytes"]
            total_installed += package["installed_bytes_estimate"]
            for entry in package["entries"]:
                self.assertTrue(entry["commercial_use_approved"])
                self.assertTrue(entry["license_id"])
                self.assertTrue(entry["source_url"].startswith("https://"))
                self.assertNotIn(entry["source_url"], RETIRED_VOICE_SOURCE_URLS)
        self.assertEqual(total_download, 716_581_281)
        self.assertLessEqual(total_installed, 1_700_000_000)

    def test_farsi_amir_is_retired_not_in_install_catalog(self):
        self.assertNotIn("fa", ALL_VOICE_PACKAGE_IDS)
        self.assertNotIn("fa", ALL_VOICE_CAPTION_LANGUAGES)
        self.assertIn(
            "https://huggingface.co/rhasspy/piper-voices/tree/main/fa/fa_IR/amir/medium",
            RETIRED_VOICE_SOURCE_URLS,
        )

    def test_public_catalog_omits_download_urls_and_checksums(self):
        catalog = public_voice_catalog()
        self.assertEqual([item["id"] for item in catalog], list(ALL_VOICE_PACKAGE_IDS))
        for item in catalog:
            self.assertNotIn("url", item)
            self.assertNotIn("sha256", item)
            self.assertIn("license_id", item)
            self.assertIn("notice", item)

    def test_selection_rejects_unknown_or_empty_packages(self):
        self.assertEqual(normalise_voice_package_selection(["zh", "es", "zh"]), ("zh", "es"))
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            normalise_voice_package_selection(["unknown"])
        with self.assertRaisesRegex(ValueError, "Select at least one"):
            normalise_voice_package_selection([])

    def test_reviewed_package_detection_requires_the_catalogue_source(self):
        spanish_source = VOICE_PACKAGES["es"]["entries"][0]["source_url"]
        configured = {
            "es": {"source_url": spanish_source},
            "fr": {"source_url": "https://example.invalid/custom-french-voice"},
        }
        self.assertEqual(installed_reviewed_voice_package_ids(configured), ("es",))

    def test_uninstall_removes_only_selected_reviewed_model_and_preserves_custom_voice(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spanish = VOICE_PACKAGES["es"]
            spanish_folder = root / "voices" / spanish["folder"]
            spanish_folder.mkdir(parents=True)
            (spanish_folder / "model.onnx").write_bytes(b"reviewed-model")
            custom_folder = root / "voices" / "custom-fr"
            custom_folder.mkdir()
            (custom_folder / "model.onnx").write_bytes(b"custom-model")
            spanish_entry = dict(spanish["entries"][0])
            custom_entry = {
                "language": "fr",
                "source_url": "https://example.invalid/custom-french-voice",
                "license_id": "Custom",
                "engine": "vits",
                "model": "voices/custom-fr/model.onnx",
                "tokens": "voices/custom-fr/tokens.txt",
                "commercial_use_approved": True,
            }
            manifest = root / "voices.json"
            manifest.write_text(json.dumps({"schema_version": 1, "voices": [spanish_entry, custom_entry]}), encoding="utf-8")

            result = uninstall_reviewed_voice_packages(manifest, ("es",))

            self.assertEqual(result["removed_package_ids"], ["es"])
            self.assertEqual(result["removed_languages"], ["es"])
            self.assertGreater(result["reclaimed_bytes"], 0)
            self.assertFalse(spanish_folder.exists())
            self.assertTrue(custom_folder.exists())
            retained = json.loads(manifest.read_text(encoding="utf-8"))["voices"]
            self.assertEqual(retained, [custom_entry])

    def test_release_contains_the_notice_copied_beside_installed_voices(self):
        notice = Path("docs/legal/SPOKEN_LANGUAGE_MODELS.md")
        self.assertTrue(notice.is_file())
        text = notice.read_text(encoding="utf-8")
        self.assertIn("No obvious commercial prohibition", text)
        self.assertIn("attribution", text)
        self.assertIn("ShareAlike", text)


if __name__ == "__main__":
    unittest.main()

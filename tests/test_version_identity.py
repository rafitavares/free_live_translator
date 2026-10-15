import re
import unittest
from pathlib import Path


class VersionIdentityTests(unittest.TestCase):
    def test_v080_code_and_settings_identity_match(self):
        source = Path("app/settings.py").read_text(encoding="utf-8")
        code_version = re.search(r'^APP_VERSION = "([^"]+)"$', source, re.MULTILINE)
        settings_version = re.search(r'^    app_version: str = "([^"]+)"$', source, re.MULTILINE)
        self.assertIsNotNone(code_version)
        self.assertIsNotNone(settings_version)
        self.assertEqual(code_version.group(1), "0.8.0")
        self.assertEqual(settings_version.group(1), code_version.group(1))

    def test_environment_example_matches_code_identity(self):
        source = Path("env.example").read_text(encoding="utf-8")
        self.assertIn("APP_VERSION=0.8.0", source)

    def test_current_browser_assets_use_v080_cache_identity(self):
        for name in ("captions", "display", "obs"):
            template = Path(f"app/templates/{name}.html").read_text(encoding="utf-8")
            self.assertIn("v=0.8.0-ui-1", template)


if __name__ == "__main__":
    unittest.main()

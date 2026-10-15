import os
import unittest
from types import SimpleNamespace
from unittest import mock

from app import networking


class LocalHostnameTests(unittest.TestCase):
    def tearDown(self):
        networking.detected_local_hostname.cache_clear()
        networking.local_hostname_is_configured.cache_clear()

    def test_linux_without_configured_hostname_exposes_setup_candidate(self):
        networking.detected_local_hostname.cache_clear()
        networking.local_hostname_is_configured.cache_clear()
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(networking, "get_settings", return_value=SimpleNamespace(caption_local_hostname=None)), \
             mock.patch.object(networking.platform, "system", return_value="Linux"), \
             mock.patch.object(networking.socket, "gethostname", return_value="caption-box"):
            self.assertEqual(networking.detected_local_hostname(), "caption-box.local")
            self.assertFalse(networking.local_hostname_is_configured())

    def test_linux_respects_explicit_local_hostname(self):
        networking.detected_local_hostname.cache_clear()
        networking.local_hostname_is_configured.cache_clear()
        with mock.patch.dict(os.environ, {"CAPTION_LOCAL_HOSTNAME": "captions.church.lan"}, clear=True), \
             mock.patch.object(networking.platform, "system", return_value="Linux"):
            self.assertEqual(networking.detected_local_hostname(), "captions.church.lan")
            self.assertTrue(networking.local_hostname_is_configured())

    def test_operator_template_keeps_hostname_qr_visible_when_unconfigured(self):
        from pathlib import Path

        operator = Path("app/templates/operator.html").read_text(encoding="utf-8")
        hostname_card = operator.index('<img src="/qr.png"')
        direct_ip_card = operator.index('<img src="/qr-ip.png"')
        self.assertLess(hostname_card, direct_ip_card)
        self.assertIn("Optional hostname · setup required", operator)
        self.assertIn("Recommended direct connection", operator)

    def test_linux_reads_local_hostname_from_settings(self):
        networking.detected_local_hostname.cache_clear()
        networking.local_hostname_is_configured.cache_clear()
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(networking, "get_settings", return_value=SimpleNamespace(caption_local_hostname="captions.church.lan")), \
             mock.patch.object(networking.platform, "system", return_value="Linux"):
            self.assertEqual(networking.detected_local_hostname(), "captions.church.lan")
            self.assertTrue(networking.local_hostname_is_configured())


if __name__ == "__main__":
    unittest.main()

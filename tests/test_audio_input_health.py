import unittest
from pathlib import Path

import numpy as np

from app.transcription.audio_input import audio_input_health, silent_input_warning


class AudioInputHealthTests(unittest.TestCase):
    def test_digital_silence_warns_only_after_grace_period(self):
        silence = np.zeros(1600, dtype=np.float32)
        seen, warning = audio_input_health(
            silence,
            stream_started_at=100.0,
            now=102.0,
            nonzero_seen=False,
        )
        self.assertFalse(seen)
        self.assertIsNone(warning)

        seen, warning = audio_input_health(
            silence,
            stream_started_at=100.0,
            now=103.1,
            nonzero_seen=False,
        )
        self.assertFalse(seen)
        self.assertIn("No audio signal", warning or "")

    def test_any_real_sample_clears_the_warning_for_the_stream(self):
        signal = np.zeros(1600, dtype=np.float32)
        signal[40] = 0.001
        seen, warning = audio_input_health(
            signal,
            stream_started_at=100.0,
            now=104.0,
            nonzero_seen=False,
        )
        self.assertTrue(seen)
        self.assertIsNone(warning)

        seen, warning = audio_input_health(
            np.zeros(1600, dtype=np.float32),
            stream_started_at=100.0,
            now=110.0,
            nonzero_seen=seen,
        )
        self.assertTrue(seen)
        self.assertIsNone(warning)

    def test_platform_help_is_specific_without_stopping_capture(self):
        mac_warning = silent_input_warning("Darwin")
        self.assertIn("Privacy & Security", mac_warning)
        self.assertIn("clamshell mode", mac_warning)
        self.assertIn("external input", mac_warning)
        self.assertIn("desktop-app access", silent_input_warning("Windows"))
        self.assertIn("PipeWire", silent_input_warning("Linux"))

    def test_both_backends_open_audio_before_loading_the_model(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ("app/transcription/faster_whisper_live.py", "app/transcription/whisper_live.py"):
            source = (root / relative).read_text(encoding="utf-8")
            stream = source.split("async def stream", 1)[1].split("while self._running", 1)[0]
            self.assertLess(stream.index("self._start_audio_stream()"), stream.index("self._load_model"))
            self.assertIn("audio_input_warning=input_warning", source)
            self.assertIn("audio_stream_open=False", source)
            self.assertIn("self._mark_audio_callback(now)", source)
            self.assertIn("self._recover_audio_stream_if_stalled", source)

    def test_operator_shows_the_non_fatal_audio_warning(self):
        root = Path(__file__).resolve().parents[1]
        operator = (root / "app/templates/operator.html").read_text(encoding="utf-8")
        styles = (root / "app/static/styles.css").read_text(encoding="utf-8")
        main = (root / "app/main.py").read_text(encoding="utf-8")
        self.assertIn('id="audioInputWarning"', operator)
        self.assertIn("data.metrics?.audio_input_warning", operator)
        self.assertIn("audioInputWarning.classList.toggle('visible', Boolean(warning))", operator)
        self.assertIn(".operator-start-notice[hidden]", styles)
        self.assertIn("display: none !important", styles)
        self.assertNotIn("microphone=()", main)

    def test_operator_dashboard_card_rows_share_the_same_height(self):
        root = Path(__file__).resolve().parents[1]
        styles = (root / "app/static/styles.css").read_text(encoding="utf-8")
        dashboard_grid = styles.split(".dashboard-grid {", 1)[1].split("}", 1)[0]
        self.assertIn("align-items: stretch", dashboard_grid)


if __name__ == "__main__":
    unittest.main()

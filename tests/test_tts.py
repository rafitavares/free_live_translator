import asyncio
import base64
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from app.tts import TranslationSpeechManager, _wav_from_float_samples


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.messages.append(json.dumps(payload))

    async def send_text(self, payload):
        self.messages.append(payload)


class FakeVoice:
    def __init__(self, pack, **_kwargs):
        self.pack = pack

    def synthesise(self, text):
        return b"RIFF-test-wave", 22050, 0.25


def write_manifest(folder: Path) -> Path:
    voice_dir = folder / "voices" / "fa"
    voice_dir.mkdir(parents=True)
    (voice_dir / "model.onnx").write_bytes(b"model")
    (voice_dir / "tokens.txt").write_text("token 0\n", encoding="utf-8")
    data_dir = folder / "voices" / "espeak-ng-data"
    data_dir.mkdir(parents=True)
    manifest = folder / "voices.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "voices": [{
            "language": "fa",
            "spoken_locale": "fa-IR",
            "engine": "vits",
            "model": "voices/fa/model.onnx",
            "tokens": "voices/fa/tokens.txt",
            "data_dir": "voices/espeak-ng-data",
            "speaker_id": 0,
            "speed": 1.0,
            "license_id": "CC0-1.0",
            "source_url": "https://example.org/model-card",
            "commercial_use_approved": True,
        }],
    }), encoding="utf-8")
    return manifest


class TranslationSpeechManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        manifest = write_manifest(Path(self.temp.name))
        self.manager = TranslationSpeechManager(
            manifest_path=manifest,
            voice_factory=FakeVoice,
            runtime_probe=lambda: True,
        )

    async def asyncTearDown(self):
        await self.manager.shutdown()
        self.temp.cleanup()

    async def test_voice_is_public_only_after_license_approval_and_resources_exist(self):
        self.assertEqual(self.manager.public_state()["available_languages"], ["fa"])
        self.assertTrue(self.manager.public_state()["enabled"])

    async def test_wav_conversion_repairs_a_small_number_of_invalid_samples(self):
        samples = np.sin(np.linspace(0, np.pi * 8, 2000, dtype=np.float32)) * 0.2
        samples[250] = np.nan

        payload, duration = _wav_from_float_samples(samples, 16000)

        with wave.open(io.BytesIO(payload), "rb") as audio:
            pcm = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
            self.assertEqual(audio.getframerate(), 16000)
        self.assertAlmostEqual(duration, 0.125)
        self.assertTrue(np.any(pcm != 0))

    async def test_wav_conversion_rejects_invalid_or_silent_voice_output(self):
        with self.assertRaisesRegex(RuntimeError, "invalid audio"):
            _wav_from_float_samples(np.full(100, np.nan, dtype=np.float32), 16000)
        with self.assertRaisesRegex(RuntimeError, "silent audio"):
            _wav_from_float_samples(np.zeros(100, dtype=np.float32), 16000)

    async def test_no_listener_means_no_synthesis_queue(self):
        queued = self.manager.queue_translation(language="fa", cue_id="cue-1", text="سلام")
        self.assertFalse(queued)
        self.assertEqual(self.manager.diagnostics_state()["queue_depths"], {})

    async def test_one_generation_is_shared_with_all_language_listeners(self):
        first = FakeWebSocket()
        second = FakeWebSocket()
        await self.manager.connect(first, "fa")
        await self.manager.connect(second, "fa")
        self.assertTrue(self.manager.queue_translation(language="fa", cue_id="cue-2", text="سلام دوستان"))
        for _ in range(100):
            packets = [json.loads(message) for message in first.messages if json.loads(message).get("type") == "translation_audio"]
            if packets:
                break
            await asyncio.sleep(0.01)
        first_packets = [json.loads(message) for message in first.messages if json.loads(message).get("type") == "translation_audio"]
        second_packets = [json.loads(message) for message in second.messages if json.loads(message).get("type") == "translation_audio"]
        self.assertEqual(len(first_packets), 1)
        self.assertEqual(len(second_packets), 1)
        self.assertEqual(base64.b64decode(first_packets[0]["audio_base64"]), b"RIFF-test-wave")
        self.assertEqual(self.manager.diagnostics_state()["generated"]["fa"], 1)

    async def test_unapproved_manifest_fails_closed(self):
        payload = json.loads(self.manager.manifest_path.read_text(encoding="utf-8"))
        payload["voices"][0]["commercial_use_approved"] = False
        self.manager.manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        self.manager.reload_manifest()
        self.assertFalse(self.manager.public_state()["enabled"])
        self.assertIn("commercial_use_approved", self.manager.diagnostics_state()["voice_errors"]["fa"])

    async def test_retired_voice_source_fails_closed(self):
        payload = json.loads(self.manager.manifest_path.read_text(encoding="utf-8"))
        payload["voices"][0]["source_url"] = (
            "https://huggingface.co/rhasspy/piper-voices/tree/main/fa/fa_IR/amir/medium"
        )
        self.manager.manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        self.manager.reload_manifest()
        self.assertFalse(self.manager.public_state()["enabled"])
        self.assertIn("retired", self.manager.diagnostics_state()["voice_errors"]["fa"])

    async def test_source_language_is_never_offered(self):
        websocket = FakeWebSocket()
        await self.manager.connect(websocket, "en")
        self.assertNotIn(websocket, self.manager._clients)
        self.assertEqual(json.loads(websocket.messages[-1])["status"], "unavailable")

    async def test_missing_runtime_fails_closed_before_listener_registration(self):
        manager = TranslationSpeechManager(
            manifest_path=self.manager.manifest_path,
            voice_factory=FakeVoice,
            runtime_probe=lambda: False,
        )
        websocket = FakeWebSocket()
        try:
            self.assertFalse(manager.public_state()["enabled"])
            self.assertEqual(manager.public_state()["available_languages"], [])
            await manager.connect(websocket, "fa")
            self.assertNotIn(websocket, manager._clients)
            self.assertEqual(json.loads(websocket.messages[-1])["status"], "unavailable")
        finally:
            await manager.shutdown()

    async def test_queue_is_bounded_before_worker_yields(self):
        listener = FakeWebSocket()
        await self.manager.connect(listener, "fa")
        self.assertTrue(self.manager.queue_translation(language="fa", cue_id="one", text="one"))
        self.assertTrue(self.manager.queue_translation(language="fa", cue_id="two", text="two"))
        self.assertTrue(self.manager.queue_translation(language="fa", cue_id="three", text="three"))
        diagnostics = self.manager.diagnostics_state()
        self.assertEqual(diagnostics["queue_depths"]["fa"], 2)
        self.assertEqual(diagnostics["dropped"]["fa"], 1)

    async def test_manifest_error_does_not_expose_local_folder(self):
        self.manager.manifest_path.write_text("{", encoding="utf-8")
        self.manager.reload_manifest()
        diagnostics = self.manager.diagnostics_state()
        self.assertFalse(diagnostics["manifest_valid"])
        self.assertNotIn(self.temp.name, diagnostics["manifest_error"])

    async def test_sensitive_mode_clears_pending_and_blocks_new_speech(self):
        listener = FakeWebSocket()
        await self.manager.connect(listener, "fa")
        self.manager.set_sensitive_mode(True)
        self.assertFalse(self.manager.queue_translation(language="fa", cue_id="private", text="private text"))
        self.assertEqual(self.manager.diagnostics_state()["queue_depths"], {})

    async def test_operator_can_disable_and_restore_translated_audio(self):
        listener = FakeWebSocket()
        await self.manager.connect(listener, "fa")
        self.assertTrue(self.manager.queue_translation(language="fa", cue_id="queued", text="queued speech"))

        self.manager.set_operator_enabled(False)
        state = self.manager.public_state()
        self.assertFalse(state["operator_enabled"])
        self.assertFalse(state["enabled"])
        self.assertEqual(state["available_languages"], [])
        self.assertEqual(self.manager.diagnostics_state()["queue_depths"], {})
        self.assertFalse(self.manager.queue_translation(language="fa", cue_id="blocked", text="blocked speech"))

        new_listener = FakeWebSocket()
        await self.manager.connect(new_listener, "fa")
        self.assertNotIn(new_listener, self.manager._clients)
        self.assertEqual(json.loads(new_listener.messages[-1])["status"], "unavailable")

        self.manager.set_operator_enabled(True)
        restored = self.manager.public_state()
        self.assertTrue(restored["operator_enabled"])
        self.assertTrue(restored["enabled"])
        self.assertEqual(restored["available_languages"], ["fa"])


if __name__ == "__main__":
    unittest.main()

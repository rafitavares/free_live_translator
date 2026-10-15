import unittest
from unittest.mock import patch

from app.transcription.audio_watchdog import AudioStreamWatchdog


class _FakeStream:
    def __init__(self):
        self.aborted = False
        self.closed = False

    def abort(self):
        self.aborted = True

    def close(self):
        self.closed = True


class _WatchdogHarness(AudioStreamWatchdog):
    def __init__(self):
        self._audio_stream_started_at = 0.0
        self._stream = _FakeStream()
        self._model = object()
        self.reset_count = 0
        self.start_count = 0
        self.fail_start = False
        self.restart_now = 0.0
        self._initialise_audio_watchdog()

    def reset_buffer(self):
        self.reset_count += 1

    def _start_audio_stream(self):
        self.start_count += 1
        if self.fail_start:
            raise RuntimeError("simulated Windows input reopen failure")
        self._stream = _FakeStream()
        self._mark_audio_stream_started(self.restart_now)


class AudioStreamWatchdogTests(unittest.TestCase):
    def test_fresh_callback_heartbeat_does_not_restart_a_healthy_stream(self):
        watchdog = _WatchdogHarness()
        watchdog._mark_audio_stream_started(100.0)
        watchdog._mark_audio_callback(102.0)

        self.assertIsNone(watchdog._recover_audio_stream_if_stalled(104.9))
        self.assertEqual(watchdog.start_count, 0)
        self.assertFalse(watchdog._stream.aborted)

    def test_stalled_callback_reopens_input_and_discards_stale_audio_state(self):
        watchdog = _WatchdogHarness()
        stale_stream = watchdog._stream
        loaded_model = watchdog._model
        watchdog._mark_audio_stream_started(100.0)
        watchdog.restart_now = 104.0

        with patch("app.transcription.audio_watchdog.record_audio_watchdog_event") as record:
            result = watchdog._recover_audio_stream_if_stalled(104.0)

        self.assertEqual(result, "recovered")
        self.assertTrue(stale_stream.aborted)
        self.assertTrue(stale_stream.closed)
        self.assertEqual(watchdog.reset_count, 1)
        self.assertEqual(watchdog.start_count, 1)
        self.assertIs(watchdog._model, loaded_model)
        self.assertEqual([call.args[0] for call in record.call_args_list], ["stall", "restart"])

    def test_failed_reopen_uses_bounded_backoff_before_retrying(self):
        watchdog = _WatchdogHarness()
        watchdog._mark_audio_stream_started(100.0)
        watchdog.fail_start = True

        with patch("app.transcription.audio_watchdog.record_audio_watchdog_event") as record:
            self.assertEqual(watchdog._recover_audio_stream_if_stalled(104.0), "failed")
            self.assertIsNone(watchdog._recover_audio_stream_if_stalled(109.9))
            self.assertEqual(watchdog._recover_audio_stream_if_stalled(110.1), "failed")

        self.assertEqual(watchdog.start_count, 2)
        self.assertEqual(
            [call.args[0] for call in record.call_args_list],
            ["stall", "failure", "stall", "failure"],
        )


if __name__ == "__main__":
    unittest.main()

"""Recover an input stream whose callback stopped without reporting an error."""
from __future__ import annotations

import logging
import time

from app.metrics import record_audio_watchdog_event, update_metrics

logger = logging.getLogger(__name__)


class AudioStreamWatchdog:
    """Small mixin for PortAudio streams used by Church Cap transcribers.

    Some Windows audio drivers can leave a stream marked active while no longer
    delivering callbacks. The transcription loop then keeps decoding the last
    rolling buffer indefinitely. A callback heartbeat is more reliable than
    the PortAudio ``active`` flag for detecting that condition.
    """

    audio_callback_stall_seconds = 3.0
    audio_restart_base_cooldown_seconds = 3.0
    audio_restart_max_cooldown_seconds = 30.0

    def _initialise_audio_watchdog(self) -> None:
        self._last_audio_callback_at = 0.0
        self._last_audio_restart_attempt_at = 0.0
        self._audio_restart_failures = 0

    def _mark_audio_stream_started(self, now: float | None = None) -> None:
        started = time.monotonic() if now is None else float(now)
        self._audio_stream_started_at = started
        # Give a newly opened stream one complete watchdog interval to deliver
        # its first callback before treating it as stalled.
        self._last_audio_callback_at = started

    def _mark_audio_callback(self, now: float | None = None) -> None:
        self._last_audio_callback_at = time.monotonic() if now is None else float(now)

    def _audio_restart_cooldown(self) -> float:
        multiplier = 2 ** min(max(0, int(self._audio_restart_failures)), 4)
        return min(
            self.audio_restart_max_cooldown_seconds,
            self.audio_restart_base_cooldown_seconds * multiplier,
        )

    def _audio_watchdog_due(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else float(now)
        heartbeat = float(self._last_audio_callback_at or self._audio_stream_started_at or current)
        if current - heartbeat < self.audio_callback_stall_seconds:
            return False
        if self._last_audio_restart_attempt_at > 0:
            if current - self._last_audio_restart_attempt_at < self._audio_restart_cooldown():
                return False
        return True

    @staticmethod
    def _close_stalled_stream(stream) -> None:
        if stream is None:
            return
        try:
            stream.abort()
        except Exception:
            try:
                stream.stop()
            except Exception:
                pass
        try:
            stream.close()
        except Exception:
            pass

    def _recover_audio_stream_if_stalled(self, now: float | None = None) -> str | None:
        """Return ``recovered``, ``failed`` or ``None`` when no action is due."""
        current = time.monotonic() if now is None else float(now)
        if not self._audio_watchdog_due(current):
            return None

        self._last_audio_restart_attempt_at = current
        stalled_for = max(0.0, current - float(self._last_audio_callback_at or current))
        logger.warning(
            "Audio callback heartbeat stopped for %.1f seconds; reopening the input stream without reloading the model.",
            stalled_for,
        )
        record_audio_watchdog_event("stall")
        update_metrics(
            audio_stream_open=False,
            has_recent_voice=False,
            audio_rms=0.0,
            audio_peak=0.0,
            audio_input_warning="Audio input stopped responding. Church Cap is reopening it automatically.",
        )
        stale_stream = getattr(self, "_stream", None)
        self._stream = None
        self._close_stalled_stream(stale_stream)
        # Never replay the last pre-stall phrase after reopening the device.
        self.reset_buffer()

        try:
            self._start_audio_stream()
        except Exception as exc:
            self._audio_restart_failures += 1
            self._last_audio_callback_at = current
            logger.warning(
                "Automatic audio input reopen failed (attempt %s); a bounded retry will follow: %s",
                self._audio_restart_failures,
                exc,
            )
            record_audio_watchdog_event("failure")
            update_metrics(
                audio_stream_open=False,
                has_recent_voice=False,
                audio_rms=0.0,
                audio_peak=0.0,
                audio_input_warning=(
                    "Audio input recovery did not succeed yet. Church Cap will retry automatically; "
                    "check the selected input and Windows microphone access."
                ),
            )
            return "failed"

        self._audio_restart_failures = 0
        logger.info("Audio input stream reopened successfully; the loaded transcription model was retained.")
        record_audio_watchdog_event("restart")
        update_metrics(
            audio_stream_open=True,
            audio_input_warning=None,
        )
        return "recovered"

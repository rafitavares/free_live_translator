"""Audio-device helpers for local live transcription.

Linux USB audio interfaces often expose capture at a native rate such as
48 kHz. Whisper still wants 16 kHz audio, so the transcribers try the requested
rate first and fall back to opening the device at its native rate when needed.
"""
from __future__ import annotations

import platform

import numpy as np
import sounddevice as sd


SILENT_INPUT_WARNING_SECONDS = 3.0


def silent_input_warning(system_name: str | None = None) -> str:
    """Return actionable help when an open device supplies digital silence."""
    system = system_name or platform.system()
    common = "No audio signal has reached Church Cap yet. Check the selected input, mixer routing, gain and mute controls."
    if system == "Darwin":
        return (
            f"{common} On macOS, the built-in MacBook microphone may be unavailable with the lid "
            "closed in clamshell mode; open the lid or select an iPhone, USB or other external input. "
            "Also allow the app used to start Church Cap (usually Terminal) in System Settings → "
            "Privacy & Security → Microphone, then restart Church Cap."
        )
    if system == "Windows":
        return (
            f"{common} On Windows, also enable microphone access and desktop-app access in "
            "Settings → Privacy & security → Microphone, then restart Church Cap."
        )
    return (
        f"{common} On Linux, also check the selected PipeWire, PulseAudio or ALSA capture source "
        "and confirm that it is not muted."
    )


def audio_input_health(
    audio: np.ndarray,
    *,
    stream_started_at: float,
    now: float,
    nonzero_seen: bool,
    warning_after_seconds: float = SILENT_INPUT_WARNING_SECONDS,
) -> tuple[bool, str | None]:
    """Track whether an opened input has ever supplied a non-zero sample."""
    if nonzero_seen or bool(audio.size and np.any(audio != 0.0)):
        return True, None
    if stream_started_at > 0 and now - stream_started_at >= max(1.0, warning_after_seconds):
        return False, silent_input_warning()
    return False, None


def input_default_sample_rate(device: str | int | None, fallback: int) -> int:
    """Return the default input sample rate for a PortAudio device."""
    try:
        info = sd.query_devices(device, "input")
    except Exception:
        try:
            info = sd.query_devices(device)
        except Exception:
            return int(fallback)
    try:
        rate = int(round(float(info.get("default_samplerate") or 0)))
    except Exception:
        rate = 0
    return rate if rate > 0 else int(fallback)


def resample_mono(audio: np.ndarray, input_rate: int, output_rate: int) -> np.ndarray:
    """Small NumPy linear resampler for mono speech audio."""
    input_rate = int(input_rate)
    output_rate = int(output_rate)
    if input_rate <= 0 or output_rate <= 0 or input_rate == output_rate or audio.size == 0:
        return audio.astype(np.float32, copy=False)
    output_size = max(1, int(round(audio.size * (output_rate / input_rate))))
    if output_size == audio.size:
        return audio.astype(np.float32, copy=False)
    source_positions = np.linspace(0.0, 1.0, num=audio.size, endpoint=False, dtype=np.float64)
    target_positions = np.linspace(0.0, 1.0, num=output_size, endpoint=False, dtype=np.float64)
    return np.interp(target_positions, source_positions, audio).astype(np.float32, copy=False)

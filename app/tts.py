from __future__ import annotations

import asyncio
import base64
import io
import importlib.util
import json
import logging
import os
import shutil
import time
import wave
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import WebSocket

from app.i18n import SOURCE_LANGUAGE, normalise_language
from app.paths import app_support_dir
from app.tts_catalog import (
    RETIRED_VOICE_SOURCE_URLS,
    VOICE_PACKAGES,
    installed_reviewed_voice_package_ids,
    normalise_voice_package_selection,
)


logger = logging.getLogger(__name__)

VOICE_MANIFEST_SCHEMA = 1
SUPPORTED_ENGINES = {"vits", "kokoro"}


def _safe_voice_tree_size(path: Path) -> int:
    """Measure an installer-owned voice folder without following links."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError("The selected voice-model folder is not a safe Church Cap directory.")
    total = 0
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_symlink():
                raise ValueError("The selected voice-model folder contains an unexpected symbolic link.")
            child = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                total += _safe_voice_tree_size(child)
            elif entry.is_file(follow_symlinks=False):
                total += entry.stat(follow_symlinks=False).st_size
            else:
                raise ValueError("The selected voice-model folder contains an unsupported filesystem item.")
    return total


def uninstall_reviewed_voice_packages(manifest_path: Path, package_ids: tuple[str, ...]) -> dict[str, Any]:
    """Remove selected reviewed model folders and their manifest entries.

    Directories are staged on the same filesystem before the manifest is
    atomically replaced. If the manifest update fails, staged folders are put
    back so Church Cap does not leave a working voice half-uninstalled.
    """
    selected = normalise_voice_package_selection(package_ids)
    manifest_path = manifest_path.expanduser()
    if manifest_path.is_symlink():
        raise ValueError("Church Cap will not modify a linked voice manifest.")
    manifest_path = manifest_path.resolve()
    root = manifest_path.parent.resolve()
    if not manifest_path.is_file():
        raise ValueError("No installed Church Cap spoken-language models were found.")
    voices_root_path = root / "voices"
    if voices_root_path.is_symlink():
        raise ValueError("Church Cap will not remove models through a linked voices folder.")
    voices_root = voices_root_path.resolve()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("The installed voice manifest could not be read safely.") from exc
    if int(payload.get("schema_version", 0)) != VOICE_MANIFEST_SCHEMA or not isinstance(payload.get("voices"), list):
        raise ValueError("The installed voice manifest is not a supported Church Cap manifest.")

    removable_keys = {
        package_id: {
            (str(entry["language"]), str(entry["source_url"]))
            for entry in VOICE_PACKAGES[package_id]["entries"]
        }
        for package_id in selected
    }
    manifest_entries = [entry for entry in payload["voices"] if isinstance(entry, dict)]
    installed = tuple(
        package_id
        for package_id in selected
        if removable_keys[package_id]
        and removable_keys[package_id].issubset({
            (str(entry.get("language") or ""), str(entry.get("source_url") or ""))
            for entry in manifest_entries
        })
    )
    if not installed:
        raise ValueError("The selected reviewed spoken-language models are not installed.")

    keys_to_remove = set().union(*(removable_keys[package_id] for package_id in installed))
    retained = [
        entry
        for entry in payload["voices"]
        if not (
            isinstance(entry, dict)
            and (str(entry.get("language") or ""), str(entry.get("source_url") or "")) in keys_to_remove
        )
    ]
    staged: list[tuple[Path, Path]] = []
    reclaimed_bytes = 0
    temporary_manifest = manifest_path.with_name(f".{manifest_path.name}.uninstall.tmp")
    if temporary_manifest.exists() or temporary_manifest.is_symlink():
        raise ValueError("A previous voice-manifest update needs attention before retrying.")
    try:
        for package_id in installed:
            folder = str(VOICE_PACKAGES[package_id]["folder"])
            target_path = voices_root / folder
            if target_path.is_symlink():
                raise ValueError("Church Cap will not remove a linked voice-model folder.")
            target = target_path.resolve()
            try:
                target.relative_to(voices_root)
            except ValueError as exc:
                raise ValueError("A reviewed voice package resolved outside the Church Cap TTS folder.") from exc
            if not target.exists():
                continue
            reclaimed_bytes += _safe_voice_tree_size(target)
            staged_path = root / f".{folder}.removing"
            if staged_path.exists() or staged_path.is_symlink():
                raise ValueError("A previous voice-model removal needs attention before retrying.")
            target.rename(staged_path)
            staged.append((target, staged_path))

        updated = {**payload, "voices": retained}
        temporary_manifest.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary_manifest.replace(manifest_path)
    except Exception:
        temporary_manifest.unlink(missing_ok=True)
        for target, staged_path in reversed(staged):
            if staged_path.exists() and not target.exists():
                staged_path.rename(target)
        raise

    for _, staged_path in staged:
        shutil.rmtree(staged_path)
    removed_languages = sorted({language for package_id in installed for language in VOICE_PACKAGES[package_id]["caption_languages"]})
    return {
        "removed_package_ids": list(installed),
        "removed_languages": removed_languages,
        "reclaimed_bytes": reclaimed_bytes,
    }


@dataclass(frozen=True)
class VoicePack:
    language: str
    spoken_locale: str
    engine: str
    model: Path
    tokens: Path
    data_dir: Path | None
    lexicon: Path | None
    voices: Path | None
    speaker_id: int
    speed: float
    license_id: str
    source_url: str
    text_conversion: str = ""


@dataclass(frozen=True)
class SpeechJob:
    language: str
    cue_id: str
    text: str
    queued_monotonic: float


def _wav_from_float_samples(samples: Any, sample_rate: int) -> tuple[bytes, float]:
    """Create a finite, audible mono PCM WAV from a voice-model result."""
    values = np.asarray(samples, dtype=np.float32)
    if values.size == 0:
        raise RuntimeError("The TTS model returned no audio.")
    finite = np.isfinite(values)
    finite_count = int(finite.sum())
    if finite_count == 0 or finite_count / values.size < 0.95:
        raise RuntimeError("The local voice generated invalid audio samples.")
    if finite_count != values.size:
        logger.warning("Translated audio repaired %s invalid model samples.", values.size - finite_count)
        values = np.nan_to_num(values, nan=0.0, posinf=1.0, neginf=-1.0)
    values = np.clip(values, -1.0, 1.0)
    rms = float(np.sqrt(np.mean(np.square(values, dtype=np.float64))))
    if not np.isfinite(rms) or rms < 1e-5:
        raise RuntimeError("The local voice generated silent audio.")
    pcm = (values * 32767.0).astype("<i2", copy=False)
    rate = max(1, int(sample_rate))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return output.getvalue(), values.size / rate


class SherpaVoice:
    """Lazily loaded Sherpa-ONNX voice with no project-time hard dependency."""

    def __init__(self, pack: VoicePack, *, num_threads: int = 2, provider: str = "cpu") -> None:
        try:
            import sherpa_onnx
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Sherpa-ONNX is not installed. Install requirements-tts.txt before enabling translated audio."
            ) from exc

        if pack.engine == "vits":
            vits = sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(pack.model),
                lexicon=str(pack.lexicon or ""),
                tokens=str(pack.tokens),
                data_dir=str(pack.data_dir or ""),
            )
            model_config = sherpa_onnx.OfflineTtsModelConfig(
                vits=vits,
                provider=provider,
                debug=False,
                num_threads=max(1, int(num_threads)),
            )
        elif pack.engine == "kokoro":
            kokoro = sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=str(pack.model),
                voices=str(pack.voices or ""),
                tokens=str(pack.tokens),
                data_dir=str(pack.data_dir or ""),
                lexicon=str(pack.lexicon or ""),
            )
            model_config = sherpa_onnx.OfflineTtsModelConfig(
                kokoro=kokoro,
                provider=provider,
                debug=False,
                num_threads=max(1, int(num_threads)),
            )
        else:  # pragma: no cover - manifest validation prevents this
            raise RuntimeError(f"Unsupported TTS engine: {pack.engine}")

        config = sherpa_onnx.OfflineTtsConfig(model=model_config, max_num_sentences=1)
        if not config.validate():
            raise RuntimeError(f"Sherpa-ONNX rejected the {pack.language} voice-pack configuration.")
        self._module = sherpa_onnx
        self._tts = sherpa_onnx.OfflineTts(config)
        self._pack = pack

    def synthesise(self, text: str) -> tuple[bytes, int, float]:
        if self._pack.text_conversion == "t2s":
            try:
                from opencc import OpenCC  # type: ignore

                text = OpenCC("t2s").convert(text)
            except Exception:
                # The Kokoro lexicon can still pronounce many shared Han
                # characters. Diagnostics retains the spoken locale so the
                # operator knows this is the Mandarin starter voice.
                logger.debug("Traditional Chinese speech conversion was unavailable; using the original caption script.")
        generation = self._module.GenerationConfig()
        generation.sid = self._pack.speaker_id
        generation.speed = self._pack.speed
        generation.silence_scale = 0.2
        audio = self._tts.generate(text, generation)
        sample_rate = int(audio.sample_rate)
        wav_bytes, duration = _wav_from_float_samples(audio.samples, sample_rate)
        return wav_bytes, sample_rate, duration


class TranslationSpeechManager:
    """Optional, bounded translated-caption speech distribution.

    Audio is generated only for final translated cues and only while at least
    one listener is subscribed to that language. Generated speech remains in
    memory just long enough to be sent; it is never written to Church Cap's
    transcript, metrics, diagnostics, or log storage.
    """

    def __init__(
        self,
        *,
        manifest_path: Path | None = None,
        num_threads: int = 2,
        provider: str = "cpu",
        max_pending_per_language: int = 2,
        max_text_characters: int = 600,
        voice_factory=SherpaVoice,
        runtime_probe=None,
        operator_enabled: bool = True,
    ) -> None:
        configured = os.getenv("CHURCH_CAP_TTS_VOICES")
        self.manifest_path = manifest_path or (
            Path(configured).expanduser() if configured else app_support_dir() / "tts" / "voices.json"
        )
        self.num_threads = max(1, int(num_threads))
        self.provider = provider if provider in {"cpu", "cuda", "coreml"} else "cpu"
        self.max_pending_per_language = max(1, int(max_pending_per_language))
        self.max_text_characters = max(80, int(max_text_characters))
        self._voice_factory = voice_factory
        self._runtime_probe = runtime_probe or (lambda: importlib.util.find_spec("sherpa_onnx") is not None)
        self._operator_enabled = bool(operator_enabled)
        self._packs: dict[str, VoicePack] = {}
        self._manifest_error = ""
        self._voice_errors: dict[str, str] = {}
        self._clients: dict[WebSocket, str] = {}
        self._queues: dict[str, deque[SpeechJob]] = {}
        self._round_robin: deque[str] = deque()
        self._queued_cues: set[tuple[str, str]] = set()
        self._recent_cues: deque[tuple[str, str]] = deque(maxlen=256)
        self._recent_cue_set: set[tuple[str, str]] = set()
        self._voices: dict[str, SherpaVoice] = {}
        self._worker_event: asyncio.Event | None = None
        self._worker_task: asyncio.Task | None = None
        self._active_job: SpeechJob | None = None
        self._last_error: dict[str, str] = {}
        self._last_latency_seconds: dict[str, float] = {}
        self._last_audio_seconds: dict[str, float] = {}
        self._sensitive_mode = False
        self._generated = Counter()
        self._dropped = Counter()
        self.reload_manifest()

    @staticmethod
    def _safe_pack_path(root: Path, value: Any, *, required: bool) -> Path | None:
        raw = str(value or "").strip()
        if not raw:
            if required:
                raise ValueError("A required voice-pack path is missing.")
            return None
        candidate = (root / raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("Voice-pack paths must remain inside the TTS folder.") from exc
        if not candidate.exists():
            raise ValueError("A voice-pack resource is missing.")
        return candidate

    def _safe_error(self, exc: Exception) -> str:
        if isinstance(exc, json.JSONDecodeError):
            return "The voice manifest is not valid JSON."
        if isinstance(exc, PermissionError):
            return "Church Cap cannot read the voice manifest or one of its resources."
        if isinstance(exc, OSError):
            return "Church Cap could not read the voice manifest or one of its resources."
        message = str(exc).strip() or exc.__class__.__name__
        for path in (self.manifest_path, self.manifest_path.parent.resolve()):
            message = message.replace(str(path), "<TTS folder>")
        return message[:400]

    def reload_manifest(self) -> None:
        self._packs = {}
        self._voices = {}
        self._manifest_error = ""
        self._voice_errors = {}
        if not self.manifest_path.exists():
            return
        try:
            root = self.manifest_path.parent.resolve()
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if int(payload.get("schema_version", 0)) != VOICE_MANIFEST_SCHEMA:
                raise ValueError(f"Expected TTS voice manifest schema {VOICE_MANIFEST_SCHEMA}.")
            voices = payload.get("voices")
            if not isinstance(voices, list):
                raise ValueError("The TTS voice manifest must contain a voices list.")
            for index, item in enumerate(voices):
                if isinstance(item, dict) and not bool(item.get("enabled", True)):
                    continue
                language_hint = f"entry_{index + 1}"
                try:
                    if not isinstance(item, dict):
                        raise ValueError("Each enabled voice entry must be an object.")
                    language = normalise_language(str(item.get("language") or ""))
                    language_hint = language or language_hint
                    if not language:
                        raise ValueError("An enabled voice entry is missing its language code.")
                    if language == SOURCE_LANGUAGE:
                        continue
                    engine = str(item.get("engine") or "").lower().strip()
                    if engine not in SUPPORTED_ENGINES:
                        raise ValueError(f"Unsupported TTS engine for {language}: {engine or 'missing'}")
                    if item.get("commercial_use_approved") is not True:
                        raise ValueError(
                            f"The {language} voice is not marked commercial_use_approved after a licence review."
                        )
                    license_id = str(item.get("license_id") or "").strip()
                    source_url = str(item.get("source_url") or "").strip()
                    if not license_id or not source_url.startswith(("https://", "http://")):
                        raise ValueError(f"The {language} voice needs license_id and source_url metadata.")
                    if source_url in RETIRED_VOICE_SOURCE_URLS:
                        raise ValueError(f"The {language} voice was retired after its base-model licence review.")
                    model = self._safe_pack_path(root, item.get("model"), required=True)
                    tokens = self._safe_pack_path(root, item.get("tokens"), required=True)
                    data_dir = self._safe_pack_path(root, item.get("data_dir"), required=False)
                    lexicon = self._safe_pack_path(root, item.get("lexicon"), required=False)
                    voices_file = self._safe_pack_path(root, item.get("voices"), required=engine == "kokoro")
                    pack = VoicePack(
                        language=language,
                        spoken_locale=str(item.get("spoken_locale") or language).strip(),
                        engine=engine,
                        model=model,  # type: ignore[arg-type]
                        tokens=tokens,  # type: ignore[arg-type]
                        data_dir=data_dir,
                        lexicon=lexicon,
                        voices=voices_file,
                        speaker_id=max(0, int(item.get("speaker_id", 0))),
                        speed=max(0.7, min(1.35, float(item.get("speed", 1.0)))),
                        license_id=license_id,
                        source_url=source_url,
                        text_conversion=str(item.get("text_conversion") or "").strip(),
                    )
                    self._packs[language] = pack
                except Exception as exc:
                    self._voice_errors[language_hint] = self._safe_error(exc)
                    logger.warning("Translated audio voice %s remains disabled: %s", language_hint, self._safe_error(exc))
                    continue
        except Exception as exc:
            self._packs = {}
            self._voice_errors = {}
            self._manifest_error = self._safe_error(exc)
            logger.warning("Translated audio remains disabled: %s", self._manifest_error)

    def public_state(self) -> dict[str, Any]:
        try:
            runtime_available = bool(self._runtime_probe())
        except Exception:
            runtime_available = False
        return {
            "enabled": self._operator_enabled and bool(self._packs) and runtime_available,
            "operator_enabled": self._operator_enabled,
            "available_languages": sorted(self._packs) if self._operator_enabled and runtime_available else [],
            "framework": "sherpa-onnx",
            "runtime_available": runtime_available,
        }

    def diagnostics_state(self) -> dict[str, Any]:
        counts = Counter(self._clients.values())
        configured_voices = {
            language: {
                "engine": pack.engine,
                "spoken_locale": pack.spoken_locale,
                "license_id": pack.license_id,
                "source_url": pack.source_url,
                "loaded": language in self._voices,
            }
            for language, pack in sorted(self._packs.items())
        }
        return {
            **self.public_state(),
            "manifest_found": self.manifest_path.exists(),
            "manifest_valid": self.manifest_path.exists() and not self._manifest_error and not self._voice_errors,
            "manifest_error": self._manifest_error,
            "voice_errors": dict(self._voice_errors),
            "configured_voices": configured_voices,
            "installed_package_ids": list(installed_reviewed_voice_package_ids(configured_voices)),
            "listener_counts": dict(counts),
            "queue_depths": {language: len(queue) for language, queue in self._queues.items() if queue},
            "active_language": self._active_job.language if self._active_job else None,
            "sensitive_mode": self._sensitive_mode,
            "generated": dict(self._generated),
            "dropped": dict(self._dropped),
            "last_latency_seconds": dict(self._last_latency_seconds),
            "last_audio_seconds": dict(self._last_audio_seconds),
            "last_error": dict(self._last_error),
            "privacy": "No generated audio or translated text is written to diagnostics or persistent storage.",
        }

    def listener_counts(self) -> dict[str, int]:
        return dict(Counter(self._clients.values()))

    def set_operator_enabled(self, enabled: bool) -> None:
        self._operator_enabled = bool(enabled)
        if self._operator_enabled:
            return
        self._queues.clear()
        self._round_robin.clear()
        self._queued_cues.clear()

    async def connect(self, websocket: WebSocket, language: str) -> None:
        language = normalise_language(language)
        await websocket.accept()
        if language == SOURCE_LANGUAGE or language not in self._packs or not self.public_state()["enabled"]:
            await websocket.send_json({
                "type": "audio_status",
                "status": "unavailable",
                "language": language,
                "message_key": "audio_unavailable",
            })
            return
        self._clients[websocket] = language
        await websocket.send_json({
            "type": "audio_status",
            "status": "listening",
            "language": language,
            "message_key": "audio_waiting",
        })

    async def disconnect(self, websocket: WebSocket) -> None:
        self._clients.pop(websocket, None)

    def queue_translation(self, *, language: str, cue_id: str, text: str) -> bool:
        language = normalise_language(language)
        text = " ".join(str(text or "").split()).strip()
        key = (language, str(cue_id))
        if (
            not text
            or not self._operator_enabled
            or self._sensitive_mode
            or language not in self._packs
            or not any(client_language == language for client_language in self._clients.values())
            or key in self._queued_cues
            or key in self._recent_cue_set
        ):
            return False
        if len(text) > self.max_text_characters:
            truncated = text[: self.max_text_characters].strip()
            text = (truncated.rsplit(" ", 1)[0].strip() or truncated)
        queue = self._queues.setdefault(language, deque())
        while len(queue) >= self.max_pending_per_language:
            removed = queue.popleft()
            self._queued_cues.discard((removed.language, removed.cue_id))
            self._dropped[language] += 1
        queue.append(SpeechJob(language, str(cue_id), text, time.monotonic()))
        self._queued_cues.add(key)
        if language not in self._round_robin:
            self._round_robin.append(language)
        self._ensure_worker()
        if self._worker_event is not None:
            self._worker_event.set()
        return True

    def set_sensitive_mode(self, enabled: bool) -> None:
        self._sensitive_mode = bool(enabled)
        if not self._sensitive_mode:
            return
        self._queues.clear()
        self._round_robin.clear()
        self._queued_cues.clear()

    def _ensure_worker(self) -> None:
        if self._worker_event is None:
            self._worker_event = asyncio.Event()
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    def _pop_next(self) -> SpeechJob | None:
        for _ in range(len(self._round_robin)):
            language = self._round_robin.popleft()
            queue = self._queues.get(language)
            if not queue:
                continue
            job = queue.popleft()
            if queue:
                self._round_robin.append(language)
            return job
        return None

    def _remember_cue(self, key: tuple[str, str]) -> None:
        if len(self._recent_cues) == self._recent_cues.maxlen:
            oldest = self._recent_cues.popleft()
            self._recent_cue_set.discard(oldest)
        self._recent_cues.append(key)
        self._recent_cue_set.add(key)

    def _synthesise(self, job: SpeechJob) -> tuple[bytes, int, float]:
        voice = self._voices.get(job.language)
        if voice is None:
            voice = self._voice_factory(
                self._packs[job.language],
                num_threads=self.num_threads,
                provider=self.provider,
            )
            self._voices[job.language] = voice
        return voice.synthesise(job.text)

    async def _worker_loop(self) -> None:
        while True:
            if self._worker_event is None:
                return
            await self._worker_event.wait()
            self._worker_event.clear()
            while True:
                job = self._pop_next()
                if job is None:
                    break
                self._active_job = job
                key = (job.language, job.cue_id)
                self._queued_cues.discard(key)
                if not any(language == job.language for language in self._clients.values()):
                    self._dropped[job.language] += 1
                    self._remember_cue(key)
                    self._active_job = None
                    continue
                started = time.monotonic()
                try:
                    wav_bytes, sample_rate, duration = await asyncio.to_thread(self._synthesise, job)
                    latency = max(0.0, time.monotonic() - started)
                    self._last_latency_seconds[job.language] = latency
                    self._last_audio_seconds[job.language] = duration
                    self._last_error.pop(job.language, None)
                    self._generated[job.language] += 1
                    if self._sensitive_mode or not self._operator_enabled:
                        self._dropped[job.language] += 1
                        continue
                    encoded = base64.b64encode(wav_bytes).decode("ascii")
                    payload = json.dumps({
                        "type": "translation_audio",
                        "language": job.language,
                        "cue_id": job.cue_id,
                        "mime_type": "audio/wav",
                        "sample_rate": sample_rate,
                        "duration_seconds": round(duration, 3),
                        "queued_seconds": round(max(0.0, started - job.queued_monotonic), 3),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "audio_base64": encoded,
                    }, separators=(",", ":"))
                    await self._broadcast_language(job.language, payload)
                except Exception as exc:
                    message = str(exc)
                    self._last_error[job.language] = message
                    logger.warning("Translated audio failed for %s: %s", job.language, exc)
                    await self._broadcast_language(job.language, json.dumps({
                        "type": "audio_status",
                        "status": "error",
                        "language": job.language,
                        "message_key": "audio_error",
                    }))
                finally:
                    self._remember_cue(key)
                    self._active_job = None

    async def _broadcast_language(self, language: str, payload: str) -> None:
        clients = [ws for ws, selected in self._clients.items() if selected == language]
        dead: list[WebSocket] = []
        for websocket in clients:
            try:
                await websocket.send_text(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self._clients.pop(websocket, None)

    async def shutdown(self) -> None:
        task = self._worker_task
        self._worker_task = None
        self._worker_event = None
        self._queues.clear()
        self._round_robin.clear()
        self._queued_cues.clear()
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

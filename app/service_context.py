"""Memory-only state and lifecycle for optional pre-service caption context."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.context_prompt import MAX_SERVICE_RECOGNITION_HINTS, build_context_prompt
from app.service_context_extractor import MAX_TERMS, ExtractionResult, extract_service_context


MAX_CORRECTIONS = 40
INACTIVE_RETENTION_SECONDS = 4 * 60 * 60


class ServiceContextError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class _CorrectionMatcher:
    pattern: re.Pattern[str]
    replacements: Mapping[str, str]

    def apply(self, text: str) -> str:
        return self.pattern.sub(
            lambda match: self.replacements.get(match.group(0).casefold(), match.group(0)),
            text,
        )


def _compile_corrections(corrections: tuple[tuple[str, str], ...]) -> _CorrectionMatcher | None:
    if not corrections:
        return None
    replacements = MappingProxyType({heard.casefold(): replacement for heard, replacement in corrections})
    alternatives = "|".join(
        re.escape(heard)
        for heard, _ in sorted(corrections, key=lambda item: len(item[0]), reverse=True)
    )
    return _CorrectionMatcher(
        pattern=re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE),
        replacements=replacements,
    )


@dataclass(frozen=True)
class ActiveServiceContext:
    initial_prompt: str | None
    hotwords: str | None
    corrections: tuple[tuple[str, str], ...]
    correction_matcher: _CorrectionMatcher | None
    included_count: int
    omitted_count: int
    prompt_token_count: int
    additional_prompt_token_count: int
    recognition_assistance_enabled: bool
    recognition_mode: str
    reference_count: int
    correction_count: int


def _clean_entry(value: object, *, max_length: int = 80) -> str:
    entry = " ".join(str(value or "").split()).strip()
    if not entry or len(entry) > max_length or any(ord(char) < 32 for char in entry):
        return ""
    return entry


class ServiceContextManager:
    def __init__(self, *, clock=time.time):
        self._clock = clock
        self._lock = threading.RLock()
        self._generation = 0
        self._state = "empty"
        self._terms: list[dict] = []
        self._references: list[dict] = []
        self._corrections: list[dict] = []
        self._active: ActiveServiceContext | None = None
        self._inactive_until: float | None = None
        self._included_count = 0
        self._omitted_count = 0
        self._prompt_token_count = 0
        self._additional_prompt_token_count = 0
        self._recognition_assistance_enabled = False
        self._source_summary = ""
        self._error = ""

    def _expire_locked(self) -> None:
        if self._state == "inactive" and self._inactive_until is not None and self._clock() >= self._inactive_until:
            self._clear_locked()

    def _clear_locked(self) -> None:
        self._generation += 1
        self._state = "empty"
        self._terms = []
        self._references = []
        self._corrections = []
        self._active = None
        self._inactive_until = None
        self._included_count = 0
        self._omitted_count = 0
        self._prompt_token_count = 0
        self._additional_prompt_token_count = 0
        self._recognition_assistance_enabled = False
        self._source_summary = ""
        self._error = ""

    def public_state(self) -> dict:
        with self._lock:
            self._expire_locked()
            remaining = max(0, int((self._inactive_until or 0) - self._clock())) if self._state == "inactive" else None
            active = self._active
            return {
                "state": self._state,
                "terms": [dict(item) for item in self._terms],
                "references": [dict(item) for item in self._references],
                "corrections": [dict(item) for item in self._corrections],
                "source_summary": self._source_summary,
                "error": self._error or None,
                "inactive_seconds_remaining": remaining,
                "active_for_service": self._state == "locked",
                "included_count": active.included_count if active else self._included_count,
                "omitted_count": active.omitted_count if active else self._omitted_count,
                "recognition_hint_limit": MAX_SERVICE_RECOGNITION_HINTS,
                "prompt_token_count": active.prompt_token_count if active else self._prompt_token_count,
                "additional_prompt_token_count": (
                    active.additional_prompt_token_count if active else self._additional_prompt_token_count
                ),
                "recognition_assistance_enabled": (
                    active.recognition_assistance_enabled if active else self._recognition_assistance_enabled
                ),
                "recognition_mode": active.recognition_mode if active else (
                    "experimental_hints" if self._recognition_assistance_enabled else "corrections_only"
                ),
            }

    def begin_analysis(self) -> int:
        with self._lock:
            if self._state == "locked":
                raise ServiceContextError("captions_running", "Stop captions before replacing service context.")
            self._generation += 1
            generation = self._generation
            self._state = "processing"
            self._error = ""
            return generation

    def analyse(self, text: str, *, source_summary: str) -> dict:
        generation = self.begin_analysis()
        try:
            result = extract_service_context(text)
        except Exception as exc:
            with self._lock:
                if generation == self._generation:
                    self._state = "empty"
                    self._error = str(exc)
            raise
        self.complete_analysis(generation, result, source_summary=source_summary)
        return self.public_state()

    def complete_analysis(self, generation: int, result: ExtractionResult, *, source_summary: str) -> bool:
        with self._lock:
            if generation != self._generation or self._state != "processing":
                return False
            self._terms = [
                {
                    "text": item.text,
                    "reason": item.reason,
                    "occurrences": item.occurrences,
                    "selected": False,
                }
                for index, item in enumerate(result.terms)
            ]
            self._references = [
                {"canonical": item.canonical, "spoken": item.spoken, "selected": True}
                for item in result.references
            ]
            self._corrections = []
            self._source_summary = source_summary
            self._inactive_until = None
            self._included_count = 0
            self._omitted_count = 0
            self._prompt_token_count = 0
            self._additional_prompt_token_count = 0
            self._recognition_assistance_enabled = False
            self._active = None
            self._state = "review"
            return True

    def cancel_analysis(self) -> dict:
        with self._lock:
            if self._state == "processing":
                self._clear_locked()
            return self.public_state()

    def approve(self, payload: dict, *, base_prompt: str | None) -> dict:
        with self._lock:
            if self._state not in {"review", "ready", "inactive"}:
                raise ServiceContextError("nothing_to_approve", "Analyse service notes before approving context.")
            recognition_assistance_enabled = bool(payload.get("recognition_assistance_enabled", False))
            terms: list[dict] = []
            seen_terms: set[str] = set()
            selected_count = 0
            for raw in list(payload.get("terms") or [])[:MAX_TERMS]:
                value = _clean_entry(raw.get("text") if isinstance(raw, dict) else raw)
                if value and value.casefold() not in seen_terms:
                    seen_terms.add(value.casefold())
                    requested = bool(raw.get("selected", True)) if isinstance(raw, dict) else True
                    selected = bool(
                        recognition_assistance_enabled
                        and requested
                        and selected_count < MAX_SERVICE_RECOGNITION_HINTS
                    )
                    selected_count += 1 if selected else 0
                    terms.append({
                        "text": value,
                        "reason": "approved by operator",
                        "occurrences": 1,
                        "selected": selected,
                    })
            references: list[dict] = []
            seen_refs: set[str] = set()
            for raw in list(payload.get("references") or [])[:40]:
                canonical = _clean_entry(raw.get("canonical") if isinstance(raw, dict) else raw, max_length=100)
                spoken = _clean_entry(raw.get("spoken") if isinstance(raw, dict) else canonical, max_length=140)
                if canonical and spoken and canonical.casefold() not in seen_refs:
                    seen_refs.add(canonical.casefold())
                    references.append({"canonical": canonical, "spoken": spoken, "selected": True})
            corrections: list[dict] = []
            seen_heard: set[str] = set()
            for raw in list(payload.get("corrections") or [])[:MAX_CORRECTIONS]:
                if not isinstance(raw, dict):
                    continue
                heard = _clean_entry(raw.get("heard_as"))
                replace = _clean_entry(raw.get("replace_with"))
                if heard and replace and heard.casefold() != replace.casefold() and heard.casefold() not in seen_heard:
                    seen_heard.add(heard.casefold())
                    corrections.append({"heard_as": heard, "replace_with": replace})
            bundle = build_context_prompt(
                base_prompt,
                (item["text"] for item in terms if item["selected"]),
                (item["canonical"] for item in references) if recognition_assistance_enabled else (),
            )
            included_keys = {item.casefold() for item in bundle.included}
            for item in terms:
                item["included"] = item["text"].casefold() in included_keys
            self._terms = terms
            self._references = references
            self._corrections = corrections
            compiled_corrections = tuple((item["heard_as"], item["replace_with"]) for item in corrections)
            self._active = ActiveServiceContext(
                initial_prompt=bundle.initial_prompt,
                hotwords=bundle.hotwords,
                corrections=compiled_corrections,
                correction_matcher=_compile_corrections(compiled_corrections),
                included_count=len(bundle.included),
                omitted_count=len(bundle.omitted),
                prompt_token_count=bundle.estimated_tokens,
                additional_prompt_token_count=bundle.additional_tokens,
                recognition_assistance_enabled=recognition_assistance_enabled,
                recognition_mode="experimental_hints" if recognition_assistance_enabled else "corrections_only",
                reference_count=len(references),
                correction_count=len(corrections),
            )
            self._included_count = len(bundle.included)
            self._omitted_count = len(bundle.omitted)
            self._prompt_token_count = bundle.estimated_tokens
            self._additional_prompt_token_count = bundle.additional_tokens
            self._recognition_assistance_enabled = recognition_assistance_enabled
            self._inactive_until = None
            self._state = "ready"
            return self.public_state()

    def lock_for_service(self) -> ActiveServiceContext | None:
        with self._lock:
            self._expire_locked()
            if self._state == "processing":
                raise ServiceContextError("analysis_in_progress", "Service notes are still being analysed.")
            if self._state != "ready" or self._active is None:
                return None
            self._state = "locked"
            return self._active

    def active_snapshot(self) -> ActiveServiceContext | None:
        with self._lock:
            return self._active if self._state == "locked" else None

    def finish_service(self) -> None:
        with self._lock:
            if self._state != "locked":
                return
            self._active = None
            self._state = "inactive"
            self._inactive_until = self._clock() + INACTIVE_RETENTION_SECONDS

    def rearm(self, *, base_prompt: str | None) -> dict:
        with self._lock:
            self._expire_locked()
            if self._state != "inactive":
                raise ServiceContextError("not_inactive", "There is no previous service context to re-arm.")
            bundle = build_context_prompt(
                base_prompt,
                (item["text"] for item in self._terms if item.get("selected")),
                (item["canonical"] for item in self._references)
                if self._recognition_assistance_enabled else (),
            )
            included_keys = {item.casefold() for item in bundle.included}
            for item in self._terms:
                item["included"] = item["text"].casefold() in included_keys
            compiled_corrections = tuple(
                (item["heard_as"], item["replace_with"]) for item in self._corrections
            )
            self._active = ActiveServiceContext(
                initial_prompt=bundle.initial_prompt,
                hotwords=bundle.hotwords,
                corrections=compiled_corrections,
                correction_matcher=_compile_corrections(compiled_corrections),
                included_count=len(bundle.included),
                omitted_count=len(bundle.omitted),
                prompt_token_count=bundle.estimated_tokens,
                additional_prompt_token_count=bundle.additional_tokens,
                recognition_assistance_enabled=self._recognition_assistance_enabled,
                recognition_mode=(
                    "experimental_hints" if self._recognition_assistance_enabled else "corrections_only"
                ),
                reference_count=len(self._references),
                correction_count=len(self._corrections),
            )
            self._included_count = len(bundle.included)
            self._omitted_count = len(bundle.omitted)
            self._prompt_token_count = bundle.estimated_tokens
            self._additional_prompt_token_count = bundle.additional_tokens
            self._inactive_until = None
            self._state = "ready"
            return self.public_state()

    def clear(self) -> dict:
        with self._lock:
            if self._state == "locked":
                raise ServiceContextError("captions_running", "Stop captions before clearing service context.")
            self._clear_locked()
            return self.public_state()

    def apply_corrections(self, text: str) -> str:
        with self._lock:
            matcher = self._active.correction_matcher if self._state == "locked" and self._active else None
        return matcher.apply(text) if matcher else text


service_context = ServiceContextManager()

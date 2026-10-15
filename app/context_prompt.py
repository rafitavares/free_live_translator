"""Build a small, auditable Whisper context prompt without splitting entries."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Iterable


MAX_SERVICE_RECOGNITION_HINTS = 2
SERVICE_PROMPT_MAX_TOKENS = 76
SERVICE_PROMPT_MAX_EXTRA_TOKENS = 8

# Most Bible references are safer and cheaper to canonicalise after
# recognition. Only book names that Whisper commonly finds difficult are
# eligible for a service recognition hint, and only when a reference to that
# book was found in the notes.
_DIFFICULT_BIBLE_BOOKS = {
    "1 chronicles",
    "2 chronicles",
    "deuteronomy",
    "ecclesiastes",
    "habakkuk",
    "haggai",
    "lamentations",
    "malachi",
    "nehemiah",
    "obadiah",
    "philemon",
    "1 thessalonians",
    "2 thessalonians",
    "zechariah",
    "zephaniah",
}


@dataclass(frozen=True)
class PromptBundle:
    initial_prompt: str | None
    hotwords: str | None
    included: tuple[str, ...]
    omitted: tuple[str, ...]
    estimated_tokens: int
    additional_tokens: int


def _default_token_count(text: str) -> int:
    """Estimate a conservative prompt budget without loading a speech backend.

    Importing ``whisper.tokenizer`` also imports OpenAI Whisper's model and
    Numba/LLVM runtime. Besides making a lightweight glossary calculation
    expensive, that caused the hardened macOS engine to initialise executable
    JIT memory even when Faster Whisper was selected. Three UTF-8 bytes per
    token is deliberately conservative for the short English prompts built
    here and keeps prompt construction independent of either backend.
    """

    return max(1, (len(text.encode("utf-8")) + 2) // 3)


def build_context_prompt(
    base_prompt: str | None,
    terms: Iterable[str],
    references: Iterable[str],
    *,
    max_tokens: int = SERVICE_PROMPT_MAX_TOKENS,
    max_extra_tokens: int = SERVICE_PROMPT_MAX_EXTRA_TOKENS,
    max_hints: int = MAX_SERVICE_RECOGNITION_HINTS,
    token_count: Callable[[str], int] = _default_token_count,
) -> PromptBundle:
    base = " ".join(str(base_prompt or "").split()).strip()
    base_tokens = token_count(base) if base else 0
    reference_values = tuple(references)
    term_values = tuple(terms)
    entries: list[str] = []
    seen: set[str] = set()
    # Preserve the extractor/operator ranking for terms. A full reference such
    # as "1 Corinthians 13:4" is deliberately not sent to Whisper; the cheap
    # formatter handles it after recognition. A difficult book name can use a
    # spare hint slot.
    for raw in term_values:
        value = " ".join(str(raw).split()).strip()
        folded = value.casefold()
        if not value or folded in seen or folded in base.casefold():
            continue
        seen.add(folded)
        entries.append(value)
    for raw in reference_values:
        canonical = " ".join(str(raw).split()).strip()
        book = re.sub(r"\s+\d.*$", "", canonical).strip()
        folded = book.casefold()
        if folded not in _DIFFICULT_BIBLE_BOOKS or folded in seen or folded in base.casefold():
            continue
        seen.add(folded)
        entries.append(book)

    included: list[str] = []
    omitted: list[str] = []
    for entry in entries:
        if len(included) >= max_hints:
            omitted.append(entry)
            continue
        candidate_entries = included + [entry]
        suffix = f"Service names: {'; '.join(candidate_entries)}."
        candidate = " ".join(item for item in (base, suffix) if item)
        candidate_tokens = token_count(candidate)
        if candidate_tokens <= max_tokens and candidate_tokens - base_tokens <= max_extra_tokens:
            included.append(entry)
        else:
            omitted.append(entry)

    suffix = f"Service names: {'; '.join(included)}." if included else ""
    prompt = " ".join(item for item in (base, suffix) if item) or None
    # Faster Whisper receives the base Christian prompt separately, so its
    # hotwords must contain every approved, budgeted service-context entry.
    # OpenAI Whisper ignores this value and uses the combined initial prompt.
    hotwords = ", ".join(included) or None
    estimated_tokens = token_count(prompt) if prompt else 0
    return PromptBundle(
        initial_prompt=prompt,
        hotwords=hotwords,
        included=tuple(included),
        omitted=tuple(omitted),
        estimated_tokens=estimated_tokens,
        additional_tokens=max(0, estimated_tokens - base_tokens),
    )

"""Bounded, deterministic extraction of useful pre-service caption context."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.bible_references import BibleReference, find_bible_references


MAX_UPLOAD_BYTES = 512 * 1024
MAX_TEXT_CHARACTERS = 100_000
MAX_PARAGRAPHS = 2_000
MAX_LINE_CHARACTERS = 4_000
MAX_TERMS = 120
MAX_TERM_CHARACTERS = 80
ALLOWED_EXTENSIONS = {".txt", ".md"}


class ServiceContextInputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExtractedTerm:
    text: str
    reason: str
    occurrences: int


@dataclass(frozen=True)
class ExtractionResult:
    terms: tuple[ExtractedTerm, ...]
    references: tuple[BibleReference, ...]
    characters_analysed: int


_COMMON = {
    "amen", "bible", "christ", "christian", "church", "god", "gospel", "holy spirit",
    "jesus", "lord", "prayer", "scripture", "sermon", "service", "today", "welcome",
    "introduction", "conclusion", "reading", "read", "verse", "chapter", "notes", "sunday",
    "theme", "title", "speaker", "series", "keywords", "key words",
}
_HEADING_PREFIXES = ("title:", "theme:", "series:", "speaker:", "reading:", "readings:", "key words:", "keywords:")
_CAPITALISED_PHRASE_RE = re.compile(
    r"(?<![\w])(?:[A-Z][\w’'\-]{2,})(?:[ \t]+(?:of|the|and|[A-Z][\w’'\-]{2,})){0,4}(?![\w])"
)
_SPECIAL_WORD_RE = re.compile(r"(?<![\w])\w{3,}(?:[-’']\w{2,})+(?![\w])", re.UNICODE)


def decode_uploaded_notes(data: bytes, filename: str) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ServiceContextInputError("file_too_large", "The notes file is larger than 512 KiB.")
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ServiceContextInputError("unsupported_file", "Choose a plain-text .txt or .md notes file.")
    if b"\x00" in data or data.startswith((b"%PDF", b"PK\x03\x04")):
        raise ServiceContextInputError("binary_file", "This does not appear to be a plain-text notes file.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ServiceContextInputError("invalid_utf8", "The notes file must use UTF-8 text encoding.") from exc


def normalise_notes(text: str) -> str:
    value = unicodedata.normalize("NFC", str(text or "")).replace("\r\n", "\n").replace("\r", "\n")
    value = "\n".join(line.rstrip() for line in value.split("\n")).strip()
    if not value:
        raise ServiceContextInputError("empty_notes", "Paste notes or choose a notes file first.")
    if "\x00" in value:
        raise ServiceContextInputError("binary_text", "The notes contain unsupported binary characters.")
    if len(value) > MAX_TEXT_CHARACTERS:
        raise ServiceContextInputError("text_too_long", "The notes are longer than 100,000 characters.")
    lines = value.splitlines()
    if len(lines) > MAX_PARAGRAPHS:
        raise ServiceContextInputError("too_many_lines", "The notes contain too many separate lines.")
    if any(len(line) > MAX_LINE_CHARACTERS for line in lines):
        raise ServiceContextInputError("line_too_long", "A line in the notes is unusually long.")
    return value


def _clean_candidate(value: str) -> str:
    value = re.sub(r"^[\s#>*+\-\d.)\]]+", "", value)
    value = re.sub(r"^(?:read|today|theme|title|speaker|series|keywords?)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[\s:;,.!?]+$", "", value)
    return " ".join(value.split()).strip()


def extract_service_context(text: str) -> ExtractionResult:
    """Extract candidates only. The caller must not retain ``text`` afterwards."""
    text = normalise_notes(text)
    scored: dict[str, dict[str, object]] = {}

    def add(raw: str, reason: str, weight: int = 1) -> None:
        candidate = _clean_candidate(raw)
        words = candidate.split()
        if not candidate or len(candidate) > MAX_TERM_CHARACTERS or len(words) > 6:
            return
        key = candidate.casefold()
        if key in _COMMON or key.isdigit() or len(key) < 3:
            return
        item = scored.setdefault(key, {"text": candidate, "score": 0, "reasons": set(), "occurrences": 0})
        item["score"] = int(item["score"]) + weight
        item["occurrences"] = int(item["occurrences"]) + 1
        reasons = item["reasons"]
        assert isinstance(reasons, set)
        reasons.add(reason)

    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.casefold()
        for prefix in _HEADING_PREFIXES:
            if lowered.startswith(prefix):
                remainder = stripped[len(prefix):]
                for part in re.split(r"[,;|]", remainder):
                    add(part, "labelled in notes", 5)
        if stripped.startswith("#") or (0 < len(stripped) <= 65 and stripped == stripped.title()):
            add(stripped, "heading", 3)

    for match in _CAPITALISED_PHRASE_RE.finditer(text):
        add(match.group(0), "name or distinctive phrase", 2)
    for match in _SPECIAL_WORD_RE.finditer(text):
        add(match.group(0), "unusual spelling", 2)

    # Repetition is useful even when a word is not capitalised, provided it is
    # long enough to be distinctive and is not common sermon prose.
    words = re.findall(r"(?u)\b[^\W\d_][\w’'\-]{7,}\b", text)
    frequencies: dict[str, tuple[str, int]] = {}
    for word in words:
        key = word.casefold()
        original, count = frequencies.get(key, (word, 0))
        frequencies[key] = (original, count + 1)
    for key, (word, count) in frequencies.items():
        if count >= 3 and key not in _COMMON:
            add(word, "repeated in notes", min(count, 5))

    ordered = sorted(
        scored.values(),
        key=lambda item: (-int(item["score"]), -int(item["occurrences"]), str(item["text"]).casefold()),
    )
    pruned: list[dict[str, object]] = []
    for item in ordered:
        key_words = str(item["text"]).casefold().split()
        if any(
            len(existing_words := str(existing["text"]).casefold().split()) > len(key_words)
            and any(existing_words[index:index + len(key_words)] == key_words for index in range(len(existing_words)))
            for existing in pruned
        ):
            continue
        pruned.append(item)
        if len(pruned) >= MAX_TERMS:
            break
    terms = tuple(
        ExtractedTerm(
            text=str(item["text"]),
            reason=", ".join(sorted(str(value) for value in item["reasons"])),
            occurrences=int(item["occurrences"]),
        )
        for item in pruned
    )
    return ExtractionResult(
        terms=terms,
        references=tuple(find_bible_references(text)),
        characters_analysed=len(text),
    )

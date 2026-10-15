"""Cheap, deterministic Bible-reference detection and caption formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BibleReference:
    canonical: str
    spoken: str


_BOOKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Genesis", ("Genesis", "Gen")), ("Exodus", ("Exodus", "Exod", "Ex")),
    ("Leviticus", ("Leviticus", "Lev")), ("Numbers", ("Numbers", "Num")),
    ("Deuteronomy", ("Deuteronomy", "Deut")), ("Joshua", ("Joshua", "Josh")),
    ("Judges", ("Judges", "Judg")), ("Ruth", ("Ruth",)),
    ("1 Samuel", ("1 Samuel", "1 Sam", "First Samuel")),
    ("2 Samuel", ("2 Samuel", "2 Sam", "Second Samuel")),
    ("1 Kings", ("1 Kings", "1 Kgs", "First Kings")),
    ("2 Kings", ("2 Kings", "2 Kgs", "Second Kings")),
    ("1 Chronicles", ("1 Chronicles", "1 Chron", "1 Chr", "First Chronicles")),
    ("2 Chronicles", ("2 Chronicles", "2 Chron", "2 Chr", "Second Chronicles")),
    ("Ezra", ("Ezra",)), ("Nehemiah", ("Nehemiah", "Neh")),
    ("Esther", ("Esther", "Esth")), ("Job", ("Job",)),
    ("Psalms", ("Psalms", "Psalm", "Ps")), ("Proverbs", ("Proverbs", "Prov")),
    ("Ecclesiastes", ("Ecclesiastes", "Eccl")),
    ("Song of Solomon", ("Song of Solomon", "Song of Songs", "Song")),
    ("Isaiah", ("Isaiah", "Isa")), ("Jeremiah", ("Jeremiah", "Jer")),
    ("Lamentations", ("Lamentations", "Lam")), ("Ezekiel", ("Ezekiel", "Ezek")),
    ("Daniel", ("Daniel", "Dan")), ("Hosea", ("Hosea", "Hos")),
    ("Joel", ("Joel",)), ("Amos", ("Amos",)), ("Obadiah", ("Obadiah", "Obad")),
    ("Jonah", ("Jonah",)), ("Micah", ("Micah", "Mic")), ("Nahum", ("Nahum", "Nah")),
    ("Habakkuk", ("Habakkuk", "Hab")), ("Zephaniah", ("Zephaniah", "Zeph")),
    ("Haggai", ("Haggai", "Hag")), ("Zechariah", ("Zechariah", "Zech")),
    ("Malachi", ("Malachi", "Mal")), ("Matthew", ("Matthew", "Matt")),
    ("Mark", ("Mark",)), ("Luke", ("Luke",)), ("John", ("John", "Jn")),
    ("Acts", ("Acts",)), ("Romans", ("Romans", "Rom")),
    ("1 Corinthians", ("1 Corinthians", "1 Cor", "First Corinthians")),
    ("2 Corinthians", ("2 Corinthians", "2 Cor", "Second Corinthians")),
    ("Galatians", ("Galatians", "Gal")), ("Ephesians", ("Ephesians", "Eph")),
    ("Philippians", ("Philippians", "Phil")), ("Colossians", ("Colossians", "Col")),
    ("1 Thessalonians", ("1 Thessalonians", "1 Thess", "First Thessalonians")),
    ("2 Thessalonians", ("2 Thessalonians", "2 Thess", "Second Thessalonians")),
    ("1 Timothy", ("1 Timothy", "1 Tim", "First Timothy")),
    ("2 Timothy", ("2 Timothy", "2 Tim", "Second Timothy")),
    ("Titus", ("Titus",)), ("Philemon", ("Philemon", "Philem")),
    ("Hebrews", ("Hebrews", "Heb")), ("James", ("James", "Jas")),
    ("1 Peter", ("1 Peter", "1 Pet", "First Peter")),
    ("2 Peter", ("2 Peter", "2 Pet", "Second Peter")),
    ("1 John", ("1 John", "1 Jn", "First John")),
    ("2 John", ("2 John", "2 Jn", "Second John")),
    ("3 John", ("3 John", "3 Jn", "Third John")),
    ("Jude", ("Jude",)), ("Revelation", ("Revelation", "Rev")),
)

_ALIAS_TO_BOOK = {
    re.sub(r"\s+", " ", alias.casefold()).strip(): canonical
    for canonical, aliases in _BOOKS for alias in aliases
}
_BOOK_PATTERN = "|".join(
    re.escape(alias) for alias in sorted(_ALIAS_TO_BOOK, key=len, reverse=True)
)
_REFERENCE_RE = re.compile(
    rf"(?<![\w])(?P<book>{_BOOK_PATTERN})\.?\s+"
    r"(?P<chapter_word>chapter\s+)?(?P<chapter>\d{1,3})"
    r"(?:\s*(?::|verse(?:s)?\s+)(?P<verses>\d{1,3}(?:\s*[-–—]\s*\d{1,3})?(?:\s*,\s*\d{1,3})*))?",
    re.IGNORECASE,
)
_AMBIGUOUS_SINGLE_WORD_BOOKS = {
    "Acts", "James", "Job", "John", "Jude", "Luke", "Mark", "Numbers", "Ruth", "Titus"
}
_REFERENCE_CUE_RE = re.compile(
    r"(?:\bbook\s+of|\bturn(?:\s+with\s+me)?\s+to|\bread(?:ing)?(?:\s+from)?|"
    r"\bletter\s+to|\bgospel\s+(?:of|according\s+to))\s*$",
    re.IGNORECASE,
)

_NUMBER_VALUES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_NUMBER_ATOM_PATTERN = "|".join(
    sorted((*_NUMBER_VALUES, "hundred"), key=len, reverse=True)
)
_NUMBER_EXPRESSION_PATTERN = (
    rf"(?:\d{{1,3}}|(?:{_NUMBER_ATOM_PATTERN})"
    rf"(?:[\s-]+(?:and[\s-]+)?(?:{_NUMBER_ATOM_PATTERN})){{0,4}})"
)
_SPOKEN_REFERENCE_RE = re.compile(
    rf"(?<![\w])(?P<book>{_BOOK_PATTERN})\.?\s*,?\s+"
    rf"chapter\s+(?P<chapter>{_NUMBER_EXPRESSION_PATTERN})"
    rf"(?:\s*,?\s+verse(?:s)?\s+(?P<verse_start>{_NUMBER_EXPRESSION_PATTERN})"
    rf"(?:\s+(?:to|through)\s+(?P<verse_end>{_NUMBER_EXPRESSION_PATTERN}))?)?",
    re.IGNORECASE,
)


def _spoken_number(value: str) -> str:
    # Digits are deliberately retained: Whisper's prompt consumes this form
    # reliably, while the surrounding words disambiguate chapter and verse.
    return value.strip()


def _canonical_book(value: str) -> str:
    key = re.sub(r"\s+", " ", value.casefold()).strip()
    return _ALIAS_TO_BOOK[key]


def _parse_spoken_number(value: str) -> int | None:
    cleaned = value.strip().casefold()
    if cleaned.isdigit():
        parsed = int(cleaned)
        return parsed if 0 < parsed <= 200 else None
    current = 0
    saw_number = False
    for token in re.split(r"[\s-]+", cleaned):
        if not token or token == "and":
            continue
        saw_number = True
        if token == "hundred":
            current = max(1, current) * 100
            continue
        number = _NUMBER_VALUES.get(token)
        if number is None:
            return None
        current += number
    return current if saw_number and 0 < current <= 200 else None


def _format_spoken_match(match: re.Match[str]) -> str:
    chapter = _parse_spoken_number(match.group("chapter"))
    verse_start = _parse_spoken_number(match.group("verse_start") or "")
    verse_end = _parse_spoken_number(match.group("verse_end") or "")
    if chapter is None or (match.group("verse_start") and verse_start is None):
        return match.group(0)
    canonical = f"{_canonical_book(match.group('book'))} {chapter}"
    if verse_start is not None:
        canonical += f":{verse_start}"
        if verse_end is not None:
            canonical += f"-{verse_end}"
    return canonical


def _digit_reference_is_confident(match: re.Match[str]) -> bool:
    canonical_book = _canonical_book(match.group("book"))
    if canonical_book not in _AMBIGUOUS_SINGLE_WORD_BOOKS or match.group("verses") or match.group("chapter_word"):
        return True
    before = match.string[max(0, match.start() - 48) : match.start()]
    if _REFERENCE_CUE_RE.search(before):
        return True
    after = match.string[match.end() : match.end() + 16]
    return bool(re.match(r"\s*(?:$|[.,;:)\]\n])", after))


def _format_digit_match(match: re.Match[str]) -> str:
    verses = re.sub(r"\s*[-–—]\s*", "-", match.group("verses") or "")
    verses = re.sub(r"\s*,\s*", ",", verses)
    canonical_book = _canonical_book(match.group("book"))
    if not _digit_reference_is_confident(match):
        return match.group(0)
    canonical = f"{canonical_book} {int(match.group('chapter'))}"
    return canonical + (f":{verses}" if verses else "")


def format_bible_references(text: str) -> str:
    """Canonicalise unambiguous Bible references without consulting service notes.

    Spoken numbers require the explicit word ``chapter`` (and normally
    ``verse``), which keeps ordinary mentions of people such as John or Mark
    outside the formatter. Numeric references retain the existing conservative
    book-plus-chapter grammar. Both patterns are compiled once at import time.
    """

    value = text or ""
    value = _SPOKEN_REFERENCE_RE.sub(_format_spoken_match, value)
    return _REFERENCE_RE.sub(_format_digit_match, value)


def find_bible_references(text: str, *, limit: int = 40) -> list[BibleReference]:
    found: list[BibleReference] = []
    seen: set[str] = set()
    for match in _REFERENCE_RE.finditer(format_bible_references(text or "")):
        if not _digit_reference_is_confident(match):
            continue
        canonical_book = _canonical_book(match.group("book"))
        chapter = match.group("chapter")
        verses = re.sub(r"\s*[-–—]\s*", "-", match.group("verses") or "")
        verses = re.sub(r"\s*,\s*", ",", verses)
        canonical = f"{canonical_book} {chapter}{':' + verses if verses else ''}"
        key = canonical.casefold()
        if key in seen:
            continue
        seen.add(key)
        if verses:
            spoken_verses = verses.replace("-", " to ").replace(",", ", ")
            spoken = f"{canonical_book}, chapter {_spoken_number(chapter)}, verses {spoken_verses}"
        else:
            spoken = f"{canonical_book}, chapter {_spoken_number(chapter)}"
        found.append(BibleReference(canonical=canonical, spoken=spoken))
        if len(found) >= limit:
            break
    return found

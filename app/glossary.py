"""Layered Christian recognition hints and safe caption corrections."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from app.context_prompt import _default_token_count


_RESOURCE_DIR = Path(__file__).with_name("resources")
PERMANENT_PROMPT_MAX_TOKENS = 68
_REFERENCE_BEFORE_RE = re.compile(
    r"(?:\bbook\s+of|\bturn(?:\s+with\s+me)?\s+to|\bread(?:ing)?(?:\s+from)?|"
    r"\bletter\s+to|\bgospel\s+(?:of|according\s+to))\s*$",
    re.IGNORECASE,
)
_REFERENCE_AFTER_RE = re.compile(
    r"^\s*(?:,\s*)?(?:chapter|chapters|verse|verses)\b",
    re.IGNORECASE,
)

# These rows shipped in the editable v0.7.5 file. Update scripts preserve that
# file, so they must not silently become broad local overrides after the safer
# versioned rules are introduced.
_LEGACY_SHIPPED_ROWS = {
    ("efficiency", "Ephesians"),
    ("effusions", "Ephesians"),
    ("ephusions", "Ephesians"),
    ("mathew", "Matthew"),
    ("thesalonians", "Thessalonians"),
    ("thessalonians", "Thessalonians"),
    ("habacook", "Habakkuk"),
    ("melchizedek", "Melchizedek"),
    ("melkezidek", "Melchizedek"),
    ("john three sixteen", "John 3:16"),
    ("romans eight", "Romans 8"),
    ("holy spirit", "Holy Spirit"),
    ("jesus christ", "Jesus Christ"),
}


@dataclass(frozen=True)
class _Rule:
    wrong: str
    correct: str
    scope: str
    source: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class _PromptTerm:
    text: str
    category: str
    priority: int


_PROMPT_CATEGORY_WEIGHTS = {
    "theology": 0.35,
    "biblical_names": 0.30,
    "bible_books_places": 0.25,
    "christian_phrases": 0.10,
}


def _builtin_resources_for_source() -> tuple[Path, Path]:
    """Fork: escolhe correções e termos embutidos pela língua do palestrante."""
    from app.source_language import SOURCE_LANGUAGE

    if SOURCE_LANGUAGE == "en":
        return _RESOURCE_DIR / "christian_corrections.csv", _RESOURCE_DIR / "christian_prompt_terms.txt"
    # Sem arquivos para a língua: nenhuma correção embutida (o glossário local continua valendo).
    return (
        _RESOURCE_DIR / f"spiritist_corrections_{SOURCE_LANGUAGE}.csv",
        _RESOURCE_DIR / f"spiritist_prompt_terms_{SOURCE_LANGUAGE}.txt",
    )


class Glossary:
    """Apply local overrides and versioned built-ins in one non-cascading pass."""

    def __init__(
        self,
        path: str | Path = "config/glossary.csv",
        *,
        builtin_path: str | Path | None = None,
        prompt_terms_path: str | Path | None = None,
    ):
        self.path = Path(path)
        default_corrections, default_terms = _builtin_resources_for_source()
        self.builtin_path = Path(builtin_path) if builtin_path else default_corrections
        self.prompt_terms_path = Path(prompt_terms_path) if prompt_terms_path else default_terms
        self.rules: list[_Rule] = []
        self.replacements: list[tuple[re.Pattern[str], str]] = []
        self.prompt_terms: tuple[str, ...] = ()
        self._prompt_entries: tuple[_PromptTerm, ...] = ()
        self.load()

    @staticmethod
    def _read_rules(path: Path, *, source: str) -> list[_Rule]:
        if not path.exists():
            return []
        rules: list[_Rule] = []
        with path.open("r", encoding="utf-8", newline="") as file_handle:
            reader = csv.DictReader(file_handle)
            for row in reader:
                wrong = (row.get("wrong") or "").strip()
                correct = (row.get("correct") or "").strip()
                if not wrong or not correct or wrong == correct:
                    continue
                if wrong.startswith("#"):  # fork: permite linhas de comentário no CSV
                    continue
                if source == "local" and (wrong.casefold(), correct) in _LEGACY_SHIPPED_ROWS:
                    continue
                scope = (row.get("scope") or "always").strip().casefold()
                if scope not in {"always", "bible_reference"}:
                    continue
                rules.append(
                    _Rule(
                        wrong=wrong,
                        correct=correct,
                        scope=scope,
                        source=source,
                        pattern=re.compile(r"(?<!\w)" + re.escape(wrong) + r"(?!\w)", re.IGNORECASE),
                    )
                )
        return rules

    def _read_prompt_terms(self) -> tuple[_PromptTerm, ...]:
        if not self.prompt_terms_path.exists():
            return ()
        terms: list[_PromptTerm] = []
        seen: set[str] = set()
        for raw_line in self.prompt_terms_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split("|", 2)]
            if len(parts) != 3:
                continue
            category, raw_priority, raw_term = parts
            term = " ".join(raw_term.split()).strip()
            try:
                priority = int(raw_priority)
            except ValueError:
                continue
            if category not in _PROMPT_CATEGORY_WEIGHTS or not term or term.casefold() in seen:
                continue
            seen.add(term.casefold())
            terms.append(_PromptTerm(text=term, category=category, priority=priority))
        return tuple(sorted(terms, key=lambda item: (-item.priority, item.text.casefold())))

    def load(self) -> None:
        builtins = self._read_rules(self.builtin_path, source="builtin")
        local = self._read_rules(self.path, source="local")

        # A church-owned row wins when it uses the same source phrase as a
        # built-in. Other matches are resolved longest-first at application.
        rules_by_key = {rule.wrong.casefold(): rule for rule in builtins}
        for rule in local:
            rules_by_key[rule.wrong.casefold()] = rule
        self.rules = list(rules_by_key.values())
        self.replacements = [(rule.pattern, rule.correct) for rule in self.rules]
        self._prompt_entries = self._read_prompt_terms()
        self.prompt_terms = tuple(entry.text for entry in self._prompt_entries)

    def initial_prompt(
        self,
        base_prompt: str | None,
        *,
        max_tokens: int = PERMANENT_PROMPT_MAX_TOKENS,
    ) -> str | None:
        """Build a bounded, category-balanced permanent recognition prompt."""

        base = " ".join(str(base_prompt or "").split()).strip()
        included: list[str] = []
        base_folded = base.casefold()
        queues = {
            category: [
                entry
                for entry in self._prompt_entries
                if entry.category == category and entry.text.casefold() not in base_folded
            ]
            for category in _PROMPT_CATEGORY_WEIGHTS
        }
        category_tokens = {category: 0 for category in _PROMPT_CATEGORY_WEIGHTS}
        current_prompt = base

        while any(queues.values()):
            # The category furthest below its weighted token share gets the
            # next opportunity. Priority controls ordering within a category.
            categories = sorted(
                (category for category, entries in queues.items() if entries),
                key=lambda category: (
                    category_tokens[category] / _PROMPT_CATEGORY_WEIGHTS[category],
                    -_PROMPT_CATEGORY_WEIGHTS[category],
                ),
            )
            added = False
            for category in categories:
                while queues[category]:
                    entry = queues[category].pop(0)
                    candidate_terms = included + [entry.text]
                    suffix = f"Christian vocabulary: {', '.join(candidate_terms)}."
                    candidate = " ".join(value for value in (base, suffix) if value)
                    if _default_token_count(candidate) > max_tokens:
                        # A shorter lower-priority entry may still fit.
                        continue
                    incremental_tokens = max(1, _default_token_count(candidate) - _default_token_count(current_prompt))
                    included.append(entry.text)
                    category_tokens[category] += incremental_tokens
                    current_prompt = candidate
                    added = True
                    break
                if added:
                    break
            if not added:
                break
        suffix = f"Christian vocabulary: {', '.join(included)}." if included else ""
        return " ".join(value for value in (base, suffix) if value) or None

    @staticmethod
    def _scope_matches(rule: _Rule, text: str, start: int, end: int) -> bool:
        if rule.scope == "always":
            return True
        before = text[max(0, start - 48) : start]
        after = text[end : min(len(text), end + 32)]
        return bool(_REFERENCE_BEFORE_RE.search(before) or _REFERENCE_AFTER_RE.search(after))

    def apply(self, text: str) -> str:
        cleaned = " ".join(text.split())
        candidates: list[tuple[int, int, int, _Rule]] = []
        for rule in self.rules:
            for match in rule.pattern.finditer(cleaned):
                if self._scope_matches(rule, cleaned, match.start(), match.end()):
                    source_priority = 0 if rule.source == "local" else 1
                    candidates.append((match.start(), match.end(), source_priority, rule))

        # Resolve against the original text, preferring the longest phrase at
        # each position. Replacements can therefore never trigger later rules.
        candidates.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
        selected: list[tuple[int, int, _Rule]] = []
        occupied_until = -1
        for start, end, _priority, rule in candidates:
            if start < occupied_until:
                continue
            selected.append((start, end, rule))
            occupied_until = end

        for start, end, rule in reversed(selected):
            cleaned = cleaned[:start] + rule.correct + cleaned[end:]
        return cleaned

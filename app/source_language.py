"""Língua falada pelo palestrante (língua de origem das legendas).

O Church Cap original assume palestras em inglês. Este fork lê a língua de
origem da variável de ambiente ``CAPTION_SOURCE_LANGUAGE`` (padrão: ``pt``).

Nota: usamos um nome próprio em vez de ``LANGUAGE`` porque ``LANGUAGE`` é uma
variável de locale comum em Linux/macOS (ex.: ``en_US:en``) e seria lida por
engano.
"""
from __future__ import annotations

import os

DEFAULT_SOURCE_LANGUAGE = "pt"

# Modelos Whisper aceitos. Os ".en" só fazem sentido para palestras em inglês.
ENGLISH_ONLY_WHISPER_MODELS = ("tiny.en", "base.en", "small.en", "medium.en")
MULTILINGUAL_WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3", "large-v3-turbo")
ALL_WHISPER_MODELS = frozenset(ENGLISH_ONLY_WHISPER_MODELS + MULTILINGUAL_WHISPER_MODELS)


def _read_dotenv_value(key: str, path: str = ".env") -> str | None:
    """Lê uma chave do .env (mesmo arquivo que app/settings.py usa)."""
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                if name.strip() == key:
                    return value.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def _read_source_language() -> str:
    raw = (
        os.environ.get("CAPTION_SOURCE_LANGUAGE")
        or _read_dotenv_value("CAPTION_SOURCE_LANGUAGE")
        or DEFAULT_SOURCE_LANGUAGE
    ).strip().lower()
    raw = raw.replace("_", "-").split("-")[0]
    return raw or DEFAULT_SOURCE_LANGUAGE


SOURCE_LANGUAGE = _read_source_language()
SOURCE_IS_ENGLISH = SOURCE_LANGUAGE == "en"

# Prompt inicial do Whisper: orienta vocabulário e língua. Um prompt em inglês
# com áudio em português empurra o Whisper a traduzir/transcrever em inglês.
DEFAULT_INITIAL_PROMPTS = {
    "en": (
        "Church service audio with prayer, Bible readings, worship, sermon, Scripture, "
        "Jesus Christ, Holy Spirit, Psalm, Psalms, Ephesians, Corinthians, Thessalonians."
    ),
    "pt": (
        "Palestra espírita em português, com prece, Evangelho Segundo o Espiritismo, "
        "Allan Kardec, perispírito, desobsessão, reencarnação, mediunidade, passe, "
        "Chico Xavier, Emmanuel, André Luiz, Joanna de Ângelis, Bezerra de Menezes."
    ),
}


def default_initial_prompt(language: str | None = None) -> str:
    return DEFAULT_INITIAL_PROMPTS.get(language or SOURCE_LANGUAGE, "")


def whisper_model_for_source(model_name: str | None, language: str | None = None) -> str:
    """Troca modelos ".en" pelo equivalente multilíngue quando a origem não é inglês."""
    language = language or SOURCE_LANGUAGE
    name = (model_name or "base.en").strip()
    if language != "en" and name.endswith(".en"):
        return name[: -len(".en")]
    return name

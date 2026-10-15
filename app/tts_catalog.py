from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


def _vits_package(
    *,
    package_id: str,
    label: str,
    language: str,
    spoken_locale: str,
    voice_key: str,
    sha256: str,
    download_bytes: int,
    installed_bytes_estimate: int,
    license_id: str,
    source_url: str,
    notice: str,
    speaker_id: int = 0,
) -> dict:
    folder = f"vits-piper-{voice_key}"
    archive = f"{folder}.tar.bz2"
    return {
        "id": package_id,
        "label": label,
        "caption_languages": [language],
        "archive": archive,
        "url": f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{archive}",
        "sha256": sha256,
        "download_bytes": download_bytes,
        "installed_bytes_estimate": installed_bytes_estimate,
        "folder": folder,
        "license_id": license_id,
        "source_url": source_url,
        "notice": notice,
        "entries": [{
            "language": language,
            "spoken_locale": spoken_locale,
            "engine": "vits",
            "model": f"voices/{folder}/{voice_key}.onnx",
            "tokens": f"voices/{folder}/tokens.txt",
            "data_dir": f"voices/{folder}/espeak-ng-data",
            "lexicon": "",
            "speaker_id": speaker_id,
            "speed": 1.0,
            "license_id": license_id,
            "source_url": source_url,
            "commercial_use_approved": True,
        }],
    }


# These packs are optional downloads. Each source model card was reviewed for
# an explicit licence with no identified commercial-use prohibition. This is a
# release-maintainer review record, not a warranty or legal advice. Keep the
# corresponding notice table in docs/legal/SPOKEN_LANGUAGE_MODELS.md in sync.
VOICE_PACKAGES: dict[str, dict] = {
    "zh": {
        "id": "zh",
        "label": "Chinese — Mandarin audio",
        "caption_languages": ["zh-hans", "zh-hant"],
        "archive": "kokoro-int8-multi-lang-v1_1.tar.bz2",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-int8-multi-lang-v1_1.tar.bz2",
        "sha256": "a1e94694776049035c4f2c6529f003aaece993c76aae9a78995831c3c4dcafc6",
        "download_bytes": 147_031_220,
        "installed_bytes_estimate": 420_000_000,
        "folder": "kokoro-int8-multi-lang-v1_1",
        "license_id": "Apache-2.0",
        "source_url": "https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh",
        "notice": "Retain the Apache 2.0 licence and notices. Traditional Chinese captions use Mandarin speech, not Cantonese.",
        "entries": [
            {
                "language": "zh-hans",
                "spoken_locale": "cmn-CN",
                "engine": "kokoro",
                "model": "voices/kokoro-int8-multi-lang-v1_1/model.int8.onnx",
                "voices": "voices/kokoro-int8-multi-lang-v1_1/voices.bin",
                "tokens": "voices/kokoro-int8-multi-lang-v1_1/tokens.txt",
                "data_dir": "voices/kokoro-int8-multi-lang-v1_1/espeak-ng-data",
                "lexicon": "voices/kokoro-int8-multi-lang-v1_1/lexicon-zh.txt",
                "speaker_id": 3,
                "speed": 1.0,
                "license_id": "Apache-2.0",
                "source_url": "https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh",
                "commercial_use_approved": True,
            },
            {
                "language": "zh-hant",
                "spoken_locale": "cmn-HK",
                "engine": "kokoro",
                "model": "voices/kokoro-int8-multi-lang-v1_1/model.int8.onnx",
                "voices": "voices/kokoro-int8-multi-lang-v1_1/voices.bin",
                "tokens": "voices/kokoro-int8-multi-lang-v1_1/tokens.txt",
                "data_dir": "voices/kokoro-int8-multi-lang-v1_1/espeak-ng-data",
                "lexicon": "voices/kokoro-int8-multi-lang-v1_1/lexicon-zh.txt",
                "speaker_id": 3,
                "speed": 1.0,
                "text_conversion": "t2s",
                "license_id": "Apache-2.0",
                "source_url": "https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh",
                "commercial_use_approved": True,
            },
        ],
    },
    "ca": _vits_package(
        package_id="ca", label="Catalan", language="ca", spoken_locale="ca-ES",
        voice_key="ca_ES-upc_ona-x_low",
        sha256="dd22f292484adb78f2ded2acdc181f75576c86019c16965684b0a25887793a7a",
        download_bytes=26_522_253, installed_bytes_estimate=90_000_000,
        license_id="CC-BY-SA-3.0-ES",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/ca/ca_ES/upc_ona/x_low",
        notice="Attribution and ShareAlike 3.0 Spain terms apply to the voice resources.",
    ),
    "es": _vits_package(
        package_id="es", label="Spanish", language="es", spoken_locale="es-MX",
        voice_key="es_MX-claude-high",
        sha256="ec33fb689c248fe64810aab564cba97babf0f506672cfd404928d46e751a4721",
        download_bytes=67_207_890, installed_bytes_estimate=130_000_000,
        license_id="Apache-2.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/claude/high",
        notice="Retain the Apache 2.0 licence and notices for the voice resources.",
    ),
    "fr": _vits_package(
        package_id="fr", label="French", language="fr", spoken_locale="fr-FR",
        voice_key="fr_FR-tom-medium",
        sha256="3d8258ef8466b5d5f2cc46c06e1415d3d01c9cbaeed8b6d5b3d152073672472c",
        download_bytes=67_202_955, installed_bytes_estimate=130_000_000,
        license_id="AGPL-3.0-only",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/tom/medium",
        notice="The voice model is AGPL-3.0-only. Preserve its licence and source offer obligations when redistributing it or a modified pack.",
    ),
    "kk": _vits_package(
        package_id="kk", label="Kazakh", language="kk", spoken_locale="kk-KZ",
        voice_key="kk_KZ-raya-x_low",
        sha256="fce067c8c078d96586fba3a429b1acbf7911a1248b04eebfebab2cf110966ce0",
        download_bytes=26_497_880, installed_bytes_estimate=90_000_000,
        license_id="CC-BY-4.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/kk/kk_KZ/raya/x_low",
        notice="Credit the voice/model source under CC BY 4.0.",
    ),
    "lv": _vits_package(
        package_id="lv", label="Latvian", language="lv", spoken_locale="lv-LV",
        voice_key="lv_LV-aivars-medium",
        sha256="a0df58c9924761e201ef75d82473b90bde32c5372267e9b4c628fdd267cf2508",
        download_bytes=67_196_173, installed_bytes_estimate=130_000_000,
        license_id="CC0-1.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/lv/lv_LV/aivars/medium",
        notice="The model card identifies the voice resources as CC0 1.0.",
    ),
    "ne": _vits_package(
        package_id="ne", label="Nepali", language="ne", spoken_locale="ne-NP",
        voice_key="ne_NP-google-x_low",
        sha256="135690fa3b6d43fe8c5f270c7bbb3fa927eed0a98d6ac07494a7ec70e7607ede",
        download_bytes=33_214_875, installed_bytes_estimate=100_000_000,
        license_id="CC-BY-SA-4.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/ne/ne_NP/google/x_low",
        notice="Attribution and ShareAlike 4.0 terms apply to the voice resources.",
    ),
    "nl": _vits_package(
        package_id="nl", label="Dutch", language="nl", spoken_locale="nl-NL",
        voice_key="nl_NL-alex-medium",
        sha256="52be645a8617eda0e592c604eb67f419fcb09376310c3ec7fc781beeb8e84bb6",
        download_bytes=67_172_584, installed_bytes_estimate=130_000_000,
        license_id="CC0-1.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/nl/nl_NL/alex/medium",
        notice="The model card identifies the source voice resources as CC0 1.0.",
    ),
    "sl": _vits_package(
        package_id="sl", label="Slovenian", language="sl", spoken_locale="sl-SI",
        voice_key="sl_SI-artur-medium",
        sha256="df805f31c4513864edebf7e287cf0b54d72788fc661ed73f88dc4e5aabc5efd5",
        download_bytes=67_025_668, installed_bytes_estimate=130_000_000,
        license_id="CC-BY-4.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/sl/sl_SI/artur/medium",
        notice="Credit the voice/model source under CC BY 4.0.",
    ),
    "sv": _vits_package(
        package_id="sv", label="Swedish", language="sv", spoken_locale="sv-SE",
        voice_key="sv_SE-alma-medium",
        sha256="4ab8212595575e52595bc95c37d0b4f79450c0f00b63496346cdc5941d913edc",
        download_bytes=67_154_700, installed_bytes_estimate=130_000_000,
        license_id="CC-BY-4.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/sv/sv_SE/alma/medium",
        notice="Credit the Alma voice and NST training-data source under CC BY 4.0.",
    ),
    "uk": _vits_package(
        package_id="uk", label="Ukrainian", language="uk", spoken_locale="uk-UA",
        voice_key="uk_UA-ukrainian_tts-medium",
        sha256="92be6ff21ebb1cbcc0c71121a6437db8d060cee5785287aaa6a19a2548f59c03",
        download_bytes=80_355_083, installed_bytes_estimate=150_000_000,
        license_id="CC0-1.0",
        source_url="https://huggingface.co/rhasspy/piper-voices/tree/main/uk/uk_UA/ukrainian_tts/medium",
        notice="The model card identifies the source voice resources as CC0 1.0.",
    ),
}

ALL_VOICE_PACKAGE_IDS = tuple(VOICE_PACKAGES)
ALL_VOICE_CAPTION_LANGUAGES = tuple(
    language
    for package in VOICE_PACKAGES.values()
    for language in package["caption_languages"]
)

# Retired after a base-model review. Existing manifests using these exact
# sources fail closed; unrelated operator-supplied custom voices are untouched.
RETIRED_VOICE_SOURCE_URLS = frozenset({
    "https://huggingface.co/rhasspy/piper-voices/tree/main/fa/fa_IR/amir/medium",
})


def public_voice_catalog() -> list[dict]:
    fields = (
        "id", "label", "caption_languages", "download_bytes",
        "installed_bytes_estimate", "license_id", "notice",
    )
    return [
        {field: deepcopy(package[field]) for field in fields}
        for package in VOICE_PACKAGES.values()
    ]


def normalise_voice_package_selection(values: Iterable[str]) -> tuple[str, ...]:
    selected: list[str] = []
    for value in values:
        package_id = str(value).strip().lower()
        if package_id and package_id not in selected:
            selected.append(package_id)
    unsupported = sorted(set(selected) - set(VOICE_PACKAGES))
    if unsupported:
        raise ValueError(f"Unsupported spoken-language package: {', '.join(unsupported)}")
    if not selected:
        raise ValueError("Select at least one spoken-language package.")
    return tuple(selected)


def installed_reviewed_voice_package_ids(
    configured_voices: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    """Return catalogue packages backed by their reviewed manifest sources.

    Matching the source as well as the language prevents an operator-supplied
    custom voice from being mistaken for a removable Church Cap download.
    """
    installed: list[str] = []
    for package_id, package in VOICE_PACKAGES.items():
        expected = {
            str(entry["language"]): str(entry["source_url"])
            for entry in package["entries"]
        }
        if expected and all(
            language in configured_voices
            and str(configured_voices[language].get("source_url") or "") == source_url
            for language, source_url in expected.items()
        ):
            installed.append(package_id)
    return tuple(installed)

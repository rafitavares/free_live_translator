# Optional Spoken-Language Model Notices

Last reviewed: 2026-08-05

Church Cap does not bundle these voice weights. An authenticated operator may choose individual packs from **Languages → Spoken translated audio** while captions are stopped. The installer downloads immutable Sherpa-ONNX release archives, verifies their pinned SHA-256 digests, and stores them in Church Cap's local application-data folder.

The review conclusion for the packs below is: **No obvious commercial prohibition; comply with attribution, notice or share-alike requirements.** This is a good-faith project review, not legal advice or a guarantee. Model code, weights, training data and generated output can have different legal considerations. Recheck the upstream terms before redistributing a voice pack, a preloaded appliance image, or a modified model.

## Included optional catalogue

| Caption language | Spoken locale | Upstream voice/model | Download | Licence recorded by model card | Required notice or action |
|---|---|---|---:|---|---|
| Chinese (Simplified) | Mandarin (`cmn-CN`) | [Kokoro 82M v1.1 zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) | 147.0 MB shared | Apache-2.0 | Retain the Apache 2.0 licence and applicable notices. |
| Chinese (Traditional, Hong Kong) | Mandarin (`cmn-HK`) | [Kokoro 82M v1.1 zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) | Shared with Simplified Chinese | Apache-2.0 | Retain the Apache 2.0 licence and notices. This is Mandarin speech, not Cantonese. |
| Catalan | `ca-ES` | [Piper UPC Ona x-low](https://huggingface.co/rhasspy/piper-voices/tree/main/ca/ca_ES/upc_ona/x_low) | 26.5 MB | CC-BY-SA-3.0-ES | Provide attribution and preserve the ShareAlike terms when redistributing or adapting the voice resource. |
| Spanish | `es-MX` | [Piper Claude high](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/claude/high) | 67.2 MB | Apache-2.0 | Retain the Apache 2.0 licence and applicable notices. |
| French | `fr-FR` | [Piper Tom medium](https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/tom/medium) | 67.2 MB | AGPL-3.0-only | Preserve the AGPL licence and meet its corresponding-source obligations when redistributing the pack or a modified version. |
| Kazakh | `kk-KZ` | [Piper Raya x-low](https://huggingface.co/rhasspy/piper-voices/tree/main/kk/kk_KZ/raya/x_low) | 26.5 MB | CC-BY-4.0 | Credit the voice/model source. Indicate changes when applicable. |
| Latvian | `lv-LV` | [Piper Aivars medium](https://huggingface.co/rhasspy/piper-voices/tree/main/lv/lv_LV/aivars/medium) | 67.2 MB | CC0-1.0 | Preserve source and review information even though attribution is not required by CC0. |
| Nepali | `ne-NP` | [Piper Google x-low](https://huggingface.co/rhasspy/piper-voices/tree/main/ne/ne_NP/google/x_low) | 33.2 MB | CC-BY-SA-4.0 | Provide attribution and preserve ShareAlike terms when redistributing or adapting the voice resource. |
| Dutch | `nl-NL` | [Piper Alex medium](https://huggingface.co/rhasspy/piper-voices/tree/main/nl/nl_NL/alex/medium) | 67.2 MB | CC0-1.0 | Preserve source and review information even though attribution is not required by CC0. |
| Slovenian | `sl-SI` | [Piper Artur medium](https://huggingface.co/rhasspy/piper-voices/tree/main/sl/sl_SI/artur/medium) | 67.0 MB | CC-BY-4.0 | Credit the voice/model and dataset source. Indicate changes when applicable. |
| Swedish | `sv-SE` | [Piper Alma medium](https://huggingface.co/rhasspy/piper-voices/tree/main/sv/sv_SE/alma/medium) | 67.1 MB | CC-BY-4.0 | Credit the Alma model and NST training-data source. Indicate changes when applicable. |
| Ukrainian | `uk-UA` | [Piper Ukrainian TTS medium](https://huggingface.co/rhasspy/piper-voices/tree/main/uk/uk_UA/ukrainian_tts/medium) | 80.3 MB | CC0-1.0 | Preserve source and review information even though attribution is not required by CC0. |

The eleven downloadable packs total approximately **716 MB**. Because archives expand and the optional Sherpa-ONNX runtime has its own dependencies, Church Cap warns that installing the complete catalogue may use approximately **1.6 GB** before runtime dependencies. These figures are estimates and vary by platform and filesystem.

## Framework and archive source

- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) is Apache-2.0 licensed. The framework licence does not replace each voice model's licence.
- Voice archives come from the official [`tts-models` Sherpa-ONNX release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models).
- Piper-compatible voice model cards come from the [rhasspy/piper-voices catalogue](https://huggingface.co/rhasspy/piper-voices). The catalogue-level MIT label must not be used as a substitute for the individual model card.
- The installer retains model cards included in upstream archives and Church Cap retains the licence identifier and source URL in its local `voices.json` manifest.

## Excluded or retired voices

The former Farsi Amir starter pack is not in this approved catalogue. Its card says it was fine-tuned from the Lessac checkpoint; the Lessac/Blizzard terms do not meet Church Cap's commercial-use requirement. Existing Church Cap manifests referencing that exact source now fail closed. Farsi translated **text** is unaffected. A future Farsi speech pack must pass a new model, base-checkpoint and training-data review.

Cantonese is also not included. Traditional Chinese captions currently map only to a Mandarin voice. Church Cap must not label that output as Cantonese.

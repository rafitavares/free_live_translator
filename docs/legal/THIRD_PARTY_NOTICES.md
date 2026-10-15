# Third-Party Notices

Last reviewed: 2026-08-06

Church Cap is released under the MIT License. This file records the direct third-party packages, optional model/tooling notes, appliance-shell system package notes, and release hygiene reminders for v0.7.6.

The repository does not vendor Python packages, Whisper model weights, Argos model packages, Homebrew packages, operating-system packages, font files, browser packages, certificates, or a prebuilt `.venv`. Installers download dependencies into the user's local environment or ask the operating system package manager to install them. If you distribute a packaged app, appliance image, wheelhouse, Docker image, or prebuilt virtual environment, generate notices from that exact artifact.

## Direct Python Dependencies

These are the direct dependencies pinned in `requirements.txt`, `requirements-translation.txt`, and the opt-in `requirements-tts.txt`.

| Component | Version | Purpose | Licence / notice |
|---|---:|---|---|
| FastAPI | 0.139.2 | Web application/API framework | MIT |
| Uvicorn | 0.34.0 | ASGI web server | BSD |
| Jinja2 | 3.1.6 | HTML templating | BSD-3-Clause |
| qrcode | 8.0 | QR code generation | BSD |
| Pillow | resolved by `qrcode[pil]` | Image handling for QR codes | HPND-style Pillow licence; exact installed version should be recorded if bundling wheels or a packaged environment |
| python-multipart | 0.0.32 | Form parsing for FastAPI routes | Apache-2.0 |
| pydantic-settings | 2.7.1 | Environment/settings loading | MIT |
| NumPy | 2.2.1 | Numerical/audio processing support | BSD-3-Clause; binary wheels may include additional notices such as OpenBLAS/LAPACK/GCC runtime components |
| sounddevice | 0.5.1 | Audio input capture | MIT; uses the system PortAudio library |
| openai-whisper | 20250625 | Default local Whisper transcription backend | MIT |
| faster-whisper | 1.2.1 | Optional lower-latency Whisper transcription backend | MIT |
| requests | 2.33.0 | Optional installer/model-download HTTP requests | Apache-2.0 |
| standard-library `http.server`, `http.client`, `subprocess`, `json`, `hashlib`, `hmac`, `secrets` | Python bundled | Appliance shell/proxy, PIN hashing, and local system commands | Python Software Foundation License; no extra package installed |
| cryptography | >=42.0.0 | Local transcript cache encryption | Apache-2.0 or BSD-3-Clause |
| argostranslate | 1.11.0 | Optional local Base translation provider installed by setup or the operator language-resource installer | MIT or CC0, per Argos Translate project metadata |
| OpenCC | 1.4.1 | Deterministic Simplified and Hong Kong Traditional Chinese script/phrase conversion after local translation | Apache-2.0 |
| ctranslate2, transformers, sentencepiece, safetensors | `ctranslate2>=4.4,<5`, `transformers<5`, `sentencepiece>=0.2.1,<0.3`, and platform-resolved `safetensors`; installed only by optional Recommended / Compatibility translation setup | Optional SMaLL-100 and Tigrinya conversion and translation runtime | MIT / Apache-2.0 / BSD-style / Apache-2.0, confirm exact resolved versions if distributing a packaged build |
| sherpa-onnx | 1.13.2, optional | Local VITS/Piper-compatible or Kokoro translated-caption speech runtime | Apache-2.0; installed only through `requirements-tts.txt`. Voice weights are separate artifacts and are not covered by the runtime licence. |

## Installer And CI Tooling Constraints

Church Cap setup and optional model installers currently use `pip==26.1.2`, `setuptools<82`, and the platform-resolved `wheel` package. GitHub security checks use `bandit==1.9.4` and `pip-audit==2.10.1`. These are installation and verification tools rather than Church Cap application-runtime imports, but packaged distributions should record the exact resolved versions they use.

Optional Linux GPU-runtime installation requests CUDA 12 `nvidia-cublas-cu12` and cuDNN 9 (`nvidia-cudnn-cu12==9.*`). The Windows source and packaged repair paths request exact compatible releases: `nvidia-cuda-runtime-cu12==12.4.127`, `nvidia-cublas-cu12==12.4.5.8`, and `nvidia-cudnn-cu12==9.1.0.70`. The packaged installer verifies the expected Windows wheel filenames and their published SHA-256 hashes before extracting the runtime DLLs and licence/notice material to per-user Church Cap application data. These wheels are not installed by default.

## Important Transitive Dependencies

The exact transitive dependency set is resolved by `pip` for the user's platform and Python version. Important runtime dependencies include:

| Component | Used by | Notice |
|---|---|---|
| Starlette | FastAPI | ASGI/web framework dependency. |
| Pydantic / pydantic-core | FastAPI and pydantic-settings | Data validation/settings dependencies. |
| python-dotenv | pydantic-settings | `.env` loading support. |
| CTranslate2 | faster-whisper and optional Fast Core translation | Local inference runtime. On Windows and Linux, Church Cap can use CUDA through CTranslate2 for Faster Whisper when the installed runtime, NVIDIA drivers, and required CUDA libraries expose it. Fast Core converts SMaLL-100 into a local CTranslate2 INT8 model when the optional installer is run. Confirm model licences and converted model distribution terms before shipping prebuilt weights. |
| PyTorch | openai-whisper | Local model runtime dependency; binary wheels may include platform-specific notices and accelerator libraries. |
| tiktoken | openai-whisper | Tokenization dependency. |
| numba / llvmlite | openai-whisper | Audio preprocessing dependencies. |
| Hugging Face Hub | faster-whisper | Model download/cache helper. |
| tokenizers | faster-whisper | Text tokenization. |
| onnxruntime | faster-whisper and optional sherpa-onnx TTS | Runtime dependency. Binary distributions may include platform-specific notices. |
| PyAV | faster-whisper | Audio decoding dependency. |
| tqdm | faster-whisper | Progress display dependency. |
| sentencepiece, stanza, sacremoses, packaging | Argos Translate | Optional translation dependencies. |
| NVIDIA CUDA Python wheel packages | Optional Windows/Linux GPU acceleration | Source setup may install packages into a local `.venv`. The packaged Windows repair path instead verifies and extracts only required DLL/licence files to per-user Church Cap application data. Windows uses the exact CUDA 12.4 runtime/cuBLAS and cuDNN 9 versions listed above; Linux may use CUDA 12 `nvidia-cublas-cu12` and cuDNN 9 `nvidia-cudnn-cu12`. They are installed only when the operator explicitly chooses GPU runtime setup. |
| PortAudio | sounddevice | System audio library installed through Homebrew on macOS or the detected Linux package manager. |

If you distribute a packaged app, wheels, a frozen environment, or a Docker image, generate a full software bill of materials from that exact artifact and include all transitive package versions and licences.

## Appliance Shell And Operating-System Packages

The AlmaLinux appliance shell is source code in this project and is covered by the Church Cap MIT License unless a file says otherwise. The shell installer does not vendor operating-system packages. It asks `dnf` to install packages from the configured AlmaLinux/EPEL/third-party repositories on the appliance.

Package names and licences can vary slightly by distribution version and repository. For a redistributed appliance image, confirm the exact RPM metadata with `rpm -qi <package>` and include the generated notices for the image you ship.

| Component / package family | Installed by | Purpose | Licence / notice |
|---|---|---|---|
| AlmaLinux packages | Appliance setup | Base operating-system packages used by the kiosk appliance | AlmaLinux is a rebuild of Red Hat Enterprise Linux sources and contains many open-source licences; include distribution notices if shipping an image |
| NetworkManager, NetworkManager-wifi, wpa_supplicant | Appliance setup | Wi-Fi scanning, connection, DHCP, and network status | Open-source system networking packages; commonly GPL/LGPL/BSD-family depending on component |
| OpenSSH server | Appliance setup | Optional PIN-gated support/admin SSH access | OpenSSH uses BSD/ISC-style open-source licences |
| Cage, Wayland stack, Firefox or Chromium | Appliance setup / kiosk launcher | Minimal kiosk browser environment | Cage is open-source; Firefox is MPL-2.0; Chromium is BSD-style plus third-party notices; browser binaries bring their own notices |
| systemd unit files | Appliance setup | Service supervision and kiosk startup | Project unit files are covered by Church Cap MIT; systemd itself is LGPL-2.1-or-later with additional notices |
| ALSA utilities, usbutils, pciutils, psmisc, acl, libinput | Appliance setup | Audio/device diagnostics, process control, permissions, and touch/input support | Open-source Linux utility packages; licences vary by package and distro build |
| Python `evdev` / `python3-evdev` | Optional appliance diagnostics | Touch/input diagnostics when standalone `evtest` is unavailable | Open-source Python package; confirm exact distro or pip metadata if bundled |
| `wvkbd`, `wvkbd-mobintl`, `squeekboard` | Optional, only if already installed | Native Wayland on-screen keyboard outside the browser | Open-source keyboard projects; not bundled by Church Cap |
| Noto Sans families including Arabic, Hebrew, Indic scripts, Thai/Lao/Khmer/Myanmar/Sinhala/Ethiopic/Armenian/Georgian, and CJK | Optional appliance setup | Better multilingual text rendering on the kiosk display | SIL Open Font License 1.1 |
| Noto Emoji / Noto Color Emoji | Optional appliance setup | Emoji/flag glyph rendering where the OS package is available | Noto emoji fonts are SIL Open Font License 1.1; related tools/resources may use Apache-2.0 or public-domain/copyright-exempt notices |
| `flag-icons` v7.3.2 | Bundled application asset subset | Local SVG language flags that render consistently on Windows, Linux and macOS | MIT; Copyright © 2013 Panayiotis Lipiridis. The complete licence is retained at `app/static/flags/LICENSE.flag-icons` |

The language metadata retains Unicode flag characters for compatibility, but the language selectors render a reviewed subset of local `flag-icons` SVG assets. Visible language-code text or fallback badges remain available if an asset cannot load.


## Project Assets And UI Language Data

- Church Cap branding images in `assets/branding/` are project assets. Unless separately stated, they are distributed with the project under the root MIT License. If you create a trademark policy later, document any trademark restrictions separately from the source-code licence.
- The client UI language catalogue in `app/locales/client_ui.json` is project-maintained interface text. It is not a model and does not contain bundled machine-translation data.
- Language flags are served locally from the bundled MIT-licensed `flag-icons` subset and do not depend on an operating-system emoji font or an external network service.

## Model And Data Notices

Church Cap does not commit or redistribute model weights in this repository.

- `openai-whisper` downloads or loads Whisper model weights at runtime according to `WHISPER_MODEL`.
- `faster-whisper` is retained as an optional lower-latency backend and downloads or loads Whisper-compatible model weights at runtime according to `WHISPER_MODEL`.
- The default model setting is `base.en`.
- Confirm the licence for every speech-to-text model you ship, cache, mirror, or bundle.
- Argos Translate language packages are downloaded by `scripts/install-translation-models-argos.sh` on macOS/Linux or `scripts/install-translation-models-argos.ps1` on Windows during setup, from the operator **Languages** page, or when the translation installer is rerun manually.
- Confirm the licence for every Argos language package you use, redistribute, or preinstall. The Argos application code is MIT/CC0, but model packages are separate artifacts and some package metadata has historically omitted an explicit licence. Do not assume the library licence automatically covers every downloaded model.
- v0.7.6 uses Argos Translate 1.11.0 and pins SentencePiece 0.2.1. Church Cap validates downloaded Argos ZIP paths, symbolic links, expansion size, encryption, and compression ratio before allowing Argos to extract a package.
- Argos 1.11.0 still pins Stanza 1.10.1. Church Cap replaces Argos sentence detection with a one-cue sentencizer before every translation because Church Cap already supplies short bounded cues; no Stanza or MiniSBD model is loaded for that path. The installed package must not be treated as safe for unrelated Stanza model loading. Reassess the pin when Argos publishes a compatible fixed dependency set.
- Optional Recommended and Compatibility translation installers pin `alirezamsh/small100` to immutable revision `8ab680e26a596d2e3d2d2d17ae0f68df1037328c`, verify the custom tokenizer SHA-256 before loading it, and prefer the repository's SafeTensors weights. The model card lists SMaLL-100 as MIT licensed and covering 101 languages. Confirm the licence again before redistributing model weights or converted CTranslate2 files.
- The optional Recommended language package includes Tigrinya text translation using `Helsinki-NLP/opus-mt-en-ti`, pinned to immutable revision `72f1e40b4b60ff4863407f90792b4fac517562ec`, and converts its SafeTensors weights locally to CTranslate2 INT8. The official model card identifies English→Tigrinya coverage and an Apache-2.0 licence. The model weights are not stored in this source repository or downloaded by normal Church Cap setup; retain the Apache 2.0 licence and notices if redistributing the downloaded weights or converted files.
- OpenCC is installed by the translation or translated-audio installers and is used only for deterministic Chinese script and regional-phrase conversion. Its official project and PyPI metadata list Apache-2.0.
- Sherpa-ONNX is an optional Apache-2.0 local speech-synthesis framework. Church Cap v0.7.6 does not bundle the runtime or any voice weights in the default installation.
- Every TTS voice pack must be reviewed separately for model-code, weight, training-data, redistribution, and commercial-use terms. Church Cap requires a source URL, licence identifier, and explicit local `commercial_use_approved` flag before a voice is enabled; those fields document an operator review but do not themselves grant rights.
- The current GPL-3.0 Piper engine is not bundled. Sherpa-ONNX can load separately reviewed Piper-compatible ONNX voice resources without installing the Piper executable.
- The optional spoken-language catalogue currently provides eleven independently selectable, checksum-pinned packs for Chinese/Mandarin, Catalan, Spanish, French, Kazakh, Latvian, Nepali, Dutch, Slovenian, Swedish and Ukrainian caption routes. Simplified and Traditional Chinese share one Mandarin pack. The source release contains none of these weights, and normal setup downloads none of them.
- The detailed source, archive size, individual model-card licence and attribution/share-alike obligations are maintained in [Optional Spoken-Language Model Notices](SPOKEN_LANGUAGE_MODELS.md). Its review conclusion is: **No obvious commercial prohibition; comply with attribution, notice or share-alike requirements.** This conclusion is not a legal warranty.
- The previously offered `vits-piper-fa_IR-amir-medium` pack is retired. Although its own dataset is marked CC0, its model card records a Lessac base checkpoint whose terms do not meet Church Cap's commercial-use requirement. Existing manifests referencing that exact source fail closed. Farsi translated text is unaffected.

Do not assume every model hosted online is safe to redistribute or use commercially. Model code, model weights, training data, and conversion scripts may have different licences.

If you add Christian-context features, prefer user-provided glossary terms, public-domain vocabulary, and church-owned sermon notes. Avoid training or fine-tuning on copyrighted Bible translations, worship lyrics, sermon libraries, or liturgical material unless you have the right to do so.

## Release Checklist

Before publishing a public release:

1. Confirm direct dependency versions are pinned in `requirements.txt`, `requirements-translation.txt`, and `requirements-tts.txt` where applicable.
2. Run a dependency vulnerability check against the exact versions being released.
3. Generate a full SBOM/licence report if distributing anything beyond source code, such as wheels, a Docker image, a bundled `.venv`, an app package, a wheelhouse, or an appliance disk image.
4. Confirm speech-to-text, translation, and TTS voice-model licences for any model weights you distribute, mirror, cache, or preinstall. Include [Optional Spoken-Language Model Notices](SPOKEN_LANGUAGE_MODELS.md) whenever optional voice packs are redistributed or preloaded.
5. If publishing the appliance shell separately, include its `LICENSE` and `THIRD_PARTY_NOTICES.md` files as well as the main app legal docs.
6. Include this file, root `LICENSE`, `docs/legal/PRIVACY.md`, `docs/legal/DISCLAIMER.md`, `.github/SECURITY.md`, and `.github/CONTRIBUTING.md`.
7. Confirm `.env`, `data/`, `certs/`, `.venv/`, logs, diagnostics exports, and local runtime files are excluded from GitHub.

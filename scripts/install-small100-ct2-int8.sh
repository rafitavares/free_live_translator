#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d ".venv" ]]; then
  echo "No .venv found. Run the setup script for this operating system first."
  exit 1
fi

source .venv/bin/activate
python scripts/report-install-progress.py 2 dependencies "Preparing translation dependencies."
python -m pip install --upgrade "pip==26.1.2" "setuptools<82" wheel
python -m pip install "ctranslate2>=4.4,<5" "transformers<5" "sentencepiece>=0.2.1,<0.3" safetensors "OpenCC==1.4.1"
python scripts/report-install-progress.py 12 model "Translation dependencies are ready."

python - <<'PY'
import hashlib
from pathlib import Path
import ctranslate2
from app.install_progress import write_install_progress
from huggingface_hub import hf_hub_download
from ctranslate2.converters import TransformersConverter

model_name = "alirezamsh/small100"
revision = "8ab680e26a596d2e3d2d2d17ae0f68df1037328c"
tokenizer_sha256 = "73c8d2405e9c588582434c9f91327127faf133b9f915b203ed07ba4cd0ca9c92"
output_dir = Path("data/models/small100-ct2-int8")
output_dir.parent.mkdir(parents=True, exist_ok=True)

if ctranslate2.contains_model(str(output_dir)):
    write_install_progress(78, "model-ready", "The SMaLL-100 INT8 model is already installed.")
    print("Fast Core / CTranslate2 INT8 model is already installed; checking the rest of the Recommended bundle...")
else:
    write_install_progress(18, "downloading", "Downloading the pinned SMaLL-100 model.", indeterminate=True)
    print(f"Downloading {model_name} tokenizer/model metadata into the local cache...")
    tokenizer_file = Path(hf_hub_download(model_name, "tokenization_small100.py", revision=revision))
    if hashlib.sha256(tokenizer_file.read_bytes()).hexdigest() != tokenizer_sha256:
        raise RuntimeError("Pinned SMaLL-100 tokenizer failed its integrity check.")
    write_install_progress(34, "converting", "Downloading remaining model files and converting SMaLL-100 to INT8.", indeterminate=True)
    print(f"Converting {model_name} to CTranslate2 INT8 at {output_dir}...")
    converter = TransformersConverter(model_name, revision=revision, trust_remote_code=False)
    converter.convert(output_dir=str(output_dir), quantization="int8", force=True)
    write_install_progress(78, "model-ready", "The SMaLL-100 INT8 model is ready.")
print("Fast Core / CTranslate2 INT8 model is installed. Enable Fast Core from the operator Languages page.")
PY

echo "Adding the bundled English-to-Tigrinya language model..."
python scripts/report-install-progress.py 82 tigrinya "Preparing the English-to-Tigrinya model."
bash scripts/install-opus-tigrinya-ct2-int8.sh
python scripts/report-install-progress.py 99 finalising "Completing Recommended language package checks."
echo "Recommended language bundle is installed, including Tigrinya."

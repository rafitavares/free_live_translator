$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "No .venv found. Run .\setup-windows.cmd first."
    exit 1
}

& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 2 "dependencies" "Preparing Compatibility package dependencies."
& $VenvPython -m pip install --upgrade "pip==26.1.2" "setuptools<82" wheel
& $VenvPython -m pip install "transformers<5" "sentencepiece>=0.2.1,<0.3" safetensors "OpenCC==1.4.1"
& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 15 "downloading" "Downloading the pinned SMaLL-100 Compatibility model." --indeterminate

$pythonScript = @'
import hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
from transformers import M2M100ForConditionalGeneration
from app.install_progress import write_install_progress

model_name = "alirezamsh/small100"
revision = "8ab680e26a596d2e3d2d2d17ae0f68df1037328c"
tokenizer_sha256 = "73c8d2405e9c588582434c9f91327127faf133b9f915b203ed07ba4cd0ca9c92"
print(f"Downloading {model_name} and its custom tokenizer into the local model cache...")
tokenizer_file = Path(hf_hub_download(model_name, "tokenization_small100.py", revision=revision))
if hashlib.sha256(tokenizer_file.read_bytes()).hexdigest() != tokenizer_sha256:
    raise RuntimeError("Pinned SMaLL-100 tokenizer failed its integrity check.")
M2M100ForConditionalGeneration.from_pretrained(model_name, revision=revision, use_safetensors=True)
write_install_progress(98, "verifying", "Checking the installed Compatibility model.")
print("Core SMaLL-100 is installed. Enable Core mode from the operator Languages page.")
'@
$pythonScript | & $VenvPython -
& $VenvPython (Join-Path $ProjectRoot "scripts\report-install-progress.py") 100 "complete" "Compatibility translation package is ready."

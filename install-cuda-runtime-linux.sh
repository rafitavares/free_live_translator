#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This CUDA runtime installer is intended for Linux." >&2
  exit 1
fi

VENV_PY="$APP_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "No .venv found. Run: bash setup-linux.sh" >&2
  exit 1
fi

# shellcheck source=scripts/linux-cuda-runtime.sh
source "$APP_DIR/scripts/linux-cuda-runtime.sh"

echo ""
echo "Installing NVIDIA CUDA 12 cuBLAS and cuDNN 9 inside Church Cap's .venv."
echo "This is optional and can be a large download."
echo "It does not install or change the system NVIDIA driver."
echo ""

"$VENV_PY" -m pip install --upgrade "pip==26.1.2" "setuptools<82" wheel
"$VENV_PY" -m pip install --upgrade --force-reinstall --no-cache-dir \
  nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

# LD_LIBRARY_PATH must be set before the Python process starts. The NVIDIA
# wheels keep their shared libraries below site-packages/nvidia/*/lib.
prepare_linux_python_cuda_library_path "$VENV_PY"

echo ""
echo "CUDA runtime packages installed. Checking GPU status again..."
"$VENV_PY" scripts/check-gpu.py

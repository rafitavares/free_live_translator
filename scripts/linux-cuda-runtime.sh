#!/usr/bin/env bash
# Helpers for exposing project-local NVIDIA CUDA wheels to the Linux loader.

linux_python_cuda_library_dirs() {
  local python_bin="$1"
  "$python_bin" - <<'PY'
from __future__ import annotations

import importlib.util
from pathlib import Path

directories: list[str] = []
for package in ("nvidia.cublas.lib", "nvidia.cudnn.lib"):
    try:
        spec = importlib.util.find_spec(package)
    except (ImportError, ModuleNotFoundError, ValueError):
        spec = None
    if spec is None:
        continue
    locations = list(spec.submodule_search_locations or [])
    if spec.origin:
        locations.append(str(Path(spec.origin).resolve().parent))
    for location in locations:
        resolved = str(Path(location).resolve())
        if Path(resolved).is_dir() and resolved not in directories:
            directories.append(resolved)

print(":".join(directories))
PY
}

prepare_linux_python_cuda_library_path() {
  local python_bin="$1"
  local cuda_library_dirs

  cuda_library_dirs="$(linux_python_cuda_library_dirs "$python_bin" 2>/dev/null || true)"
  if [[ -z "$cuda_library_dirs" ]]; then
    return 0
  fi

  if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
    export LD_LIBRARY_PATH="$cuda_library_dirs:$LD_LIBRARY_PATH"
  else
    export LD_LIBRARY_PATH="$cuda_library_dirs"
  fi
}

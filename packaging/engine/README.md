# Frozen Engine Packaging

This directory contains the Phase 1 one-folder PyInstaller proof for the Church Cap engine. The engine is an internal supervised binary, not the public macOS or Windows application by itself.

## Current position

The Apple Silicon engine proof is integrated into the signed/notarized Mac release candidate. A native Windows x64 engine candidate now uses the same entry point, protocol, data/resource contract, and spec with its own Windows dependency lock, resource mapping, and smoke evidence.

## Invariants

- Build on the target operating system and architecture.
- Use Python 3.12 and the exact packaged dependency input.
- Do not include `.env`, credentials, logs, transcripts, downloaded model weights, `.venv`, or user configuration.
- Use a one-folder build so native libraries and signing failures remain inspectable.
- Run with `CHURCH_CAP_RUNTIME_MODE=packaged` when supervised.
- Treat the application/resource tree as immutable; all mutable categories use per-user Church Cap application support.

## Apple Silicon spike

1. Run `scripts/release/check-macos-packaging-host.sh`.
2. Create the ignored `.venv-packaging` Python 3.12 environment outside the release artifact. The build scripts select it automatically when present.
3. Install `requirements-packaged.txt` into that build environment.
4. Run `scripts/release/build-engine-macos.sh`.
5. Run `scripts/release/check-macos-engine-bundle.sh` to verify required resources, every Mach-O architecture, and the proof build's ad-hoc signature. The build script also runs this automatically.
6. Run the dependency-free host smoke test:

   ```bash
   python3 scripts/release/smoke-frozen-engine.py \
     --engine dist/engine-macos-arm64/church-cap-engine/church-cap-engine
   ```

7. Run the remaining audio/model and clean-machine smoke matrix in `docs/project/DESKTOP_DISTRIBUTION_PLAN.md`.

The PyInstaller spec deliberately starts broad for dynamic ML/audio packages. After the first clean-machine evidence, replace unnecessary collection with explicit hooks rather than guessing before a successful build.

## Windows x64 spike

From a native Windows x64 PowerShell session with the project-local Python 3.12 packaging environment resolved:

```powershell
.\scripts\release\build-engine-windows.ps1
.\.venv-packaging\Scripts\python.exe .\scripts\release\smoke-frozen-engine.py `
  --engine .\dist\engine-windows-x64\church-cap-engine\church-cap-engine.exe `
  --startup-timeout 180
```

The build script invokes the shared spec and then verifies required shared resources, packaged resource preflight, and the x64 machine type of every `.exe`, `.dll`, and `.pyd`. It does not sign the internal engine.

Native Windows evidence refreshed 2026-08-22 after the dashboard-style installer and clearer CUDA retry status changes: 251 PE files are x64; packaged-resource preflight passes; and the shared frozen smoke covers setup redirect, Viewer, Operator, Display, OBS, static resources, protocol-2 lifecycle shutdown, and bundle immutability. The logical bundle is 1,053,148,432 bytes with smoke SHA-256 `abf14db801a75e9056a1149874b2e23e1915fc4bef90991f28e795ade7c4d03b`; smoke startup was 4.484 seconds. `church-cap-engine.exe` is 73,856,702 bytes with SHA-256 `8289d47d8356178b6df6fde8127ff3fd5acc83a2f9669e8758e40873ceabf303` and Authenticode status `NotSigned`.

In packaged mode the same executable also owns allow-listed resource-worker operations. Translation and spoken-language installation write progress and mutable model data beneath per-user application data and never mutate the frozen bundle. `--install-windows-cuda-runtime` installs exact checksum-pinned CUDA 12.4 runtime/cuBLAS and cuDNN 9 DLLs beneath the per-user Church Cap support directory. A source checkout continues to use the PowerShell helper and project `.venv`; the packaged repair path does not require either one.

On Windows the spec deliberately keeps `console=True` so the supervisor can receive versioned stdout/stderr lifecycle events, while `hide_console="hide-early"` provides bootloader-level defense in depth. The native desktop supervisor is a Windows GUI-subsystem executable and creates the engine with Windows `CREATE_NO_WINDOW`, redirected stdin/stdout/stderr, and Job Object ownership; this prevents console creation rather than relying on later hiding. Do not replace this design with `console=False` without redesigning and revalidating the supervisor protocol.

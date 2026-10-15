# Platform Dependency Locks

These files record exact native dependency resolutions used by desktop packaging proofs. They supplement the human-maintained requirement inputs and must be regenerated and reviewed on the named native target.

- `macos-arm64-py312.txt` — initial Apple Silicon Python 3.12 resolution created on 2026-08-12 from `requirements-packaged.txt`.
- `windows-x64-py312.txt` — native Windows x64 Python 3.12.13 feasibility resolution created on 2026-08-21; hash/source provenance remains.

The initial freeze is feasibility evidence, not the final hash-locked production input. Before a signed release, generate an artifact-specific lock with hashes/source provenance and verify that its SBOM and licence output match the frozen bundle.

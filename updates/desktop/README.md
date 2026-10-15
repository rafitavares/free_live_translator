# Desktop update channels

The installed Tauri supervisor reads one independently versioned manifest:

- `darwin-aarch64/latest.json` for the Apple Silicon Mac release;
- `windows-x86_64/latest.json` for the Windows x64 release.

Mac, Windows, and Linux artifacts are published together in one `vX.Y.Z` GitHub Release. The desktop manifests remain separate so each installed wrapper downloads only its own signed artifact. Linux and Appliance releases continue to use their CLI update route and must not publish a Tauri desktop manifest.

`latest.json` files are release outputs, not hand-written metadata. Generate one only after its platform artifact and `.sig` exist:

```text
python3 scripts/release/generate-desktop-update-manifest.py \
  --version 0.8.1 \
  --target darwin-aarch64 \
  --artifact-url https://github.com/Church-Cap/Live-Church-Captions/releases/download/v0.8.1/Church-Cap-v0.8.1-macOS-Apple-Silicon.app.tar.gz \
  --signature-file dist/Church-Cap-v0.8.1-macOS-Apple-Silicon.app.tar.gz.sig \
  --notes-file docs/project/V0.8.1_RELEASE_NOTES.md
```

Commit and publish the generated platform manifest only after its referenced GitHub Release asset is downloadable. Until a manifest exists, v0.8.0 deliberately reports that the signed update channel has not yet been published.

# Generated engine staging area

Platform-specific Tauri configuration maps the complete PyInstaller one-folder engine from its ignored `dist/` build output into `Contents/Resources/engine/church-cap-engine/` (macOS) or the equivalent Windows resource directory. It does not create a second source-tree copy. Generated engine output must not contain user data, models, credentials, logs, or signing keys.

The source resolver still expects `engine/church-cap-engine/church-cap-engine` beneath the platform resource directory. `tauri.macos.conf.json` is the first native mapping; the Windows overlay will provide the same destination contract from its independently frozen x64 engine.

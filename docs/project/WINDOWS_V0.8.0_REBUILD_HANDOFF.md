# Church Cap v0.8.0 Windows rebuild handoff

Last updated: 2026-08-25

This rebuild replaces only the superseded Windows desktop wrapper and installer after the unpublished Tauri updater key was rotated. Use source commit `7d55006` or newer from branch `release/v0.8.0-audit`. The expected updater public key ID is `BF1E020A4490108A`. Do not publish the earlier 256,013,999-byte installer.

The encrypted updater private key stays on the release Mac. It is not required to compile Windows and must not be copied to the Windows computer. Windows v0.8.0 remains Authenticode-unsigned by project-owner decision; the returned installer will receive the separate mandatory Tauri updater signature on the Mac.

## Prepare the source

1. Extract the supplied committed-source ZIP into a new short local path such as `C:\ChurchCap080`.
2. Copy the existing validated frozen engine folder from the previous Windows build workspace into:

   `C:\ChurchCap080\dist\engine-windows-x64\church-cap-engine`

3. Do not copy the previous `desktop\src-tauri\target`, `desktop\node_modules`, installer EXE, updater signature, public-key file, or Tauri configuration over the new source.
4. Confirm the active source contains `BF1E020A4490108A` and does not contain `ADA9086F8E24EB2F`:

   ```powershell
   Set-Location C:\ChurchCap080
   Select-String -Path packaging\updater\church-cap-updater-public.key,desktop\src-tauri\tauri.conf.json -Pattern 'BF1E020A4490108A'
   if (Select-String -Path desktop\src-tauri\tauri.conf.json -Pattern 'ADA9086F8E24EB2F' -Quiet) { throw 'Superseded updater key is still present.' }
   ```

## Verify and build

Run these commands in a normal x64 PowerShell session with the same Visual Studio Build Tools, Windows SDK, Rust, Node/npm, and WebView2 toolchain used for the accepted earlier candidate:

```powershell
Set-Location C:\ChurchCap080
powershell -ExecutionPolicy Bypass -File scripts\release\check-windows-engine-bundle.ps1

Set-Location desktop
npm ci
npm test

Set-Location src-tauri
cargo test --locked
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings

Set-Location ..
npm run tauri -- build --config src-tauri\tauri.windows.conf.json
```

If NSIS reports a legacy path-length failure, map the project root temporarily to a short drive letter and repeat only the Tauri build from that drive. Do not move or edit source files to shorten individual resource paths.

The generated installer is beneath `desktop\src-tauri\target\release\bundle\nsis`. Locate the newest `*setup.exe`, then copy it to:

`dist\releases\Church-Cap-v0.8.0-Windows-x64-Setup.exe`

## Verify the replacement

Run the following checks before transfer:

```powershell
$ProjectRoot = 'C:\ChurchCap080'
$HostExe = Join-Path $ProjectRoot 'desktop\src-tauri\target\release\church-cap-desktop.exe'
$Installer = Join-Path $ProjectRoot 'dist\releases\Church-Cap-v0.8.0-Windows-x64-Setup.exe'

if (-not (Test-Path -LiteralPath $HostExe -PathType Leaf)) { throw 'Desktop host was not built.' }
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw 'Renamed NSIS installer is missing.' }

$HostText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($HostExe))
if (-not $HostText.Contains('BF1E020A4490108A')) { throw 'Replacement updater key ID is not embedded in the desktop host.' }
if ($HostText.Contains('ADA9086F8E24EB2F')) { throw 'Superseded updater key ID is embedded in the desktop host.' }

$Signature = Get-AuthenticodeSignature -LiteralPath $Installer
if ($Signature.Status -ne 'NotSigned') { throw "Unexpected Authenticode status: $($Signature.Status)" }

$Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $Installer
$Installer | Get-Item | Select-Object FullName,Length,LastWriteTime
$Hash | Format-List
```

Install this exact EXE on the Windows test computer and repeat the focused clean-machine checks: normal install, no console window, browser launch, tray controls, start-at-login opt-in, password/security recovery, captions start/stop, optional resource installation, and uninstall cleanup. CUDA remains optional and should be tested on NVIDIA hardware when available.

## Return to the release Mac

Return the exact installer and its recorded SHA-256 to the release Mac. The Mac release process will:

1. verify the transferred SHA-256;
2. create `Church-Cap-v0.8.0-Windows-x64-Setup.exe.sig` with `scripts/release/sign-updater-artifact.sh` and the protected rotated key;
3. independently verify that Tauri signature against the committed public key;
4. generate the final Windows checksum file;
5. place only the replacement installer, signature, and checksum in the public release-assets folder.

Do not publish a Windows updater manifest until the GitHub Release asset is live, anonymously downloadable, checksum-verified, and the exact installer has passed the clean-machine checks.

## Rebuild execution record — 2026-08-25

- The supplied short-path source archive had no `.git` metadata, so commit/branch identity could not be independently re-read on Windows. Its committed updater key file and Tauri configuration agree and decode to public key ID `BF1E020A4490108A`.
- Only the preserved validated frozen engine folder was copied from the previous workspace. No previous Tauri target, `node_modules`, installer, updater signature, updater configuration, or NSIS tools were copied. The staged engine executable is 73,856,702 bytes with SHA-256 `8289d47d8356178b6df6fde8127ff3fd5acc83a2f9669e8758e40873ceabf303`.
- The engine bundle verifier passes all required resources, packaged preflight, and 251 x64 PE files. The lifecycle/route/immutability smoke passes Viewer, Operator setup redirect, Display, OBS, static resources, protocol 2, clean shutdown, and unchanged-bundle checks.
- The final source passes 369 shared Python tests with 1 skip and 38 subtests, 19 desktop JavaScript tests, 24 Rust tests with the one state-changing start-at-login test ignored, `cargo fmt --check`, and strict Clippy.
- The rebuilt x64 GUI host contains both the raw ID and complete encoded public key for `BF1E020A4490108A`. Neither raw ID nor encoded public key for `ADA9086F8E24EB2F` is present.
- The verified replacement is `C:\ChurchCap080\dist\releases\Church-Cap-v0.8.0-Windows-x64-Setup.exe`: 256,027,492 bytes, SHA-256 `51f7c0528811bb286848c649c1ea97a76f7450f5519f16eec15d6d1c63318e34`, Authenticode `NotSigned`.
- The release Mac created the mandatory 432-byte Tauri updater signature. Independent verification against the committed replacement public key passes; its SHA-256 is `641bb2eadc34b67ac65cd50b8b5cc5e82ac99704e85d432b4f734368ac643878`.
- The project owner subsequently confirmed that the exact final Windows candidate installs and operates correctly. Do not create the Windows updater manifest until the GitHub Release is published and this exact asset is anonymously downloadable and reverified.

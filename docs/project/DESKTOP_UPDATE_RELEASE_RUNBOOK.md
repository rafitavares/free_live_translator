# Church Cap Desktop Update Release Runbook

Last updated: 2026-08-25

Church Cap uses Tauri's mandatory updater signature independently of operating-system signing. Apple Developer ID and notarization remain required for the Mac release. Windows Authenticode is recommended for reputation and SmartScreen, but the user accepted deferring it for v0.8.0; a Tauri signature is still mandatory before Church Cap may install a Windows package through its in-app updater.

## Channels and releases

- All supported platform downloads use one GitHub tag/release, `vX.Y.Z`.
- Mac desktop channel: `updates/desktop/darwin-aarch64/latest.json`.
- Windows desktop channel: `updates/desktop/windows-x86_64/latest.json`.
- Linux CLI uses the same release's `Church-Cap-Linux-CLI.tar.gz` and `.sha256` assets through its CLI updater, not Tauri.
- Appliance remains a Linux deployment profile unless a separately installed image is introduced later.

The version inside every build remains normal semantic version text such as `0.8.1`, and the matching public release tag is `v0.8.1`. Mac and Windows retain independent signed manifests even though their artifacts share one release. Publish each manifest only after its platform artifact is anonymously downloadable and verified. A platform manifest may remain on the previous tested version if that platform's new artifact is not ready; never point it at a missing or unverified asset.

## Updater signing key

The committed public key is `packaging/updater/church-cap-updater-public.key` and is embedded in `desktop/src-tauri/tauri.conf.json`. The private key must never enter the repository, a release asset, normal logs, diagnostics, or a shared project folder.

On the current release Mac, the encrypted private key is stored outside this project and its password is protected by the macOS Keychain service `Church Cap Tauri Updater Signing Key`. Before the first public v0.8 release:

The updater key pair was rotated on 2026-08-25, before any public desktop update manifest was published, after the original encrypted key password could not be recovered. The active public key ID is `BF1E020A4490108A`. Every Mac or Windows candidate containing the earlier public key is superseded and must not be published; Linux CLI releases are unaffected.

1. Back up the encrypted private key to an independently encrypted, access-controlled location.
2. Back up the password in the project owner's password manager, separately from the key backup.
3. Restore both into an isolated directory and perform a signing probe.
4. Record who controls recovery access. Losing either item prevents existing installations from trusting future updates.

CI should receive the private key and password only through protected release-environment secrets. Unsigned build/test jobs must not receive them.

## Mac release order

1. Build the frozen engine and release-profile app from locked inputs on Apple Silicon.
2. Set `CHURCH_CAP_CODESIGN_IDENTITY` to the exact Keychain identity, `CHURCH_CAP_CODESIGN_IDENTITY_SHA1` to its 40-character certificate fingerprint, and `CHURCH_CAP_NOTARY_PROFILE` to the validated `notarytool` profile. The fingerprint selector prevents duplicate certificates with the same Apple display name from making `codesign` ambiguous while authority verification still uses the human-readable Developer ID name.
3. Run `scripts/release/sign-macos-app.sh`. It signs nested code from the inside out, verifies Developer ID, Team ID, secure timestamp, Hardened Runtime, and production entitlements, then deliberately defers Gatekeeper until notarization.
4. Run `scripts/release/notarize-macos-app.sh`. It submits a metadata-preserving ZIP, retains Apple's submission/log evidence, staples the accepted ticket to the app, and requires Gatekeeper acceptance.
5. Run `scripts/release/build-macos-updater-artifact.sh` against that exact stapled app. It rejects ad-hoc/no-Team-ID apps, creates `Church-Cap-vX.Y.Z-macOS-Apple-Silicon.app.tar.gz`, and invokes `sign-updater-artifact.sh` for its `.sig`.
6. Run `scripts/release/build-macos-dmg.sh` to create the human-facing DMG from the same stapled app. The production builder rejects internal naming, version drift, ad-hoc/no-Team-ID input, or an unstapled app.
7. Run `scripts/release/notarize-macos-dmg.sh` to sign the DMG, submit it, retain Apple's evidence, staple it, and require the final Gatekeeper assessment.
8. Upload the DMG, updater archive, `.sig`, checksums, notices, SBOM, provenance, and release notes to the draft `vX.Y.Z` release alongside the other platform assets.
9. Run clean-machine/quarantine tests, publish the unified release, and confirm the updater archive URL is anonymously downloadable.
10. Generate `updates/desktop/darwin-aarch64/latest.json` with `generate-desktop-update-manifest.py`, review its URL/version/signature, then publish that manifest in a later commit.

The v0.8.0 release Mac has a user-verified `Developer ID Application` identity for Team ID `VCFSA9YLF5`, certificate fingerprint `27744BF4CE7F2729EE04284CEB4579E6244ED9C3`, and a validated `Church Cap Notary` Keychain profile. Certificate names and fingerprints are public release metadata; no private key, certificate export, Apple password, or app-specific password belongs in this project or its logs.

The updater-key-rotation replacement app submission is `df80ba51-a1cd-40b7-a02a-36547a6c980b` and the replacement DMG submission is `beb94c82-f603-458e-a6da-ec3c1965a382`. Apple marked both `Accepted` and `Ready for distribution` with no issues. These identifiers are release evidence, not credentials.

## Windows release order

Use the matching order on a clean Windows x64 builder: frozen-engine verification, NSIS build, Authenticode signing and verification when required, Tauri `.sig`, clean-machine tests, upload to the shared `vX.Y.Z` release, confirm the asset URL, then publish `updates/desktop/windows-x86_64/latest.json` in a later commit. The shared-core and wrapper source-of-truth rules are in `CROSS_PLATFORM_ARCHITECTURE.md`; current release status is recorded in `V0.8.0_IMPLEMENTATION.md`.

## Linux release order

Build and validate `Church-Cap-Linux-CLI.tar.gz`, upload it and `Church-Cap-Linux-CLI.tar.gz.sha256` to the same `vX.Y.Z` release, then verify both URLs. The Linux updater selects GitHub's latest published non-prerelease and downloads only those two curated assets. It preserves the local environment and user data, stages and validates the replacement, and retains rollback data if replacement fails.

## Unified publication order

1. Create the `vX.Y.Z` release as a draft.
2. Upload every ready human-facing installer, updater artifact, `.sig`, and checksum.
3. Complete clean-machine checks against the exact uploaded files.
4. Publish the GitHub Release and confirm anonymous downloads.
5. Generate and commit the Mac and Windows manifests last. This commit is the point at which installed desktop applications can discover the new version.

## Required update acceptance

A release is not complete until the previous installed version:

- reports the correct new version and release notes;
- rejects missing, altered, and wrong-key signatures;
- refuses installation while captions are live, including when captions start during download;
- preserves passwords, settings, models, logs, and privacy choices;
- stops its owned engine cleanly only after verification;
- installs, relaunches, passes compatible `/health`, and reports the new running version;
- recovers honestly from network loss, full disk, locked files, installer failure, and failed post-update health.

Until a platform manifest is published, v0.8.0 displays “Update channel not published yet” and keeps running normally. Publishing a valid v0.8.0 manifest after the v0.8.0 assets are live makes the initial installations report “Church Cap is up to date” and establishes the channel before v0.8.1.

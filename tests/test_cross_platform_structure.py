"""Guard the single shared web-application source used by every platform."""

from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CrossPlatformStructureTests(unittest.TestCase):
    def test_shared_resource_directory_uses_canonical_lowercase_name(self) -> None:
        child_names = {path.name for path in (ROOT / "app").iterdir()}
        self.assertIn("resources", child_names)
        self.assertNotIn("Resources", child_names)

    def test_frozen_engine_bundles_all_shared_browser_asset_roots(self) -> None:
        spec = (ROOT / "packaging" / "engine" / "church_cap_engine.spec").read_text(
            encoding="utf-8"
        )
        for shared_path in (
            'ROOT / "app" / "templates"',
            'ROOT / "app" / "static"',
            'ROOT / "app" / "locales"',
            'ROOT / "app" / "resources"',
            'ROOT / "docs" / "legal"',
            'ROOT / "engine" / "entrypoint.py"',
        ):
            with self.subTest(shared_path=shared_path):
                self.assertIn(shared_path, spec)

    def test_desktop_wrapper_does_not_duplicate_shared_web_trees(self) -> None:
        desktop = ROOT / "desktop"
        for duplicated_path in (
            desktop / "app",
            desktop / "src" / "app",
            desktop / "src" / "templates",
            desktop / "src" / "static",
        ):
            with self.subTest(path=duplicated_path):
                self.assertFalse(duplicated_path.exists())

    def test_windows_engine_hides_console_without_disabling_protocol_pipes(self) -> None:
        spec = (ROOT / "packaging" / "engine" / "church_cap_engine.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn("console=True", spec)
        self.assertIn('hide_console="hide-early" if sys.platform == "win32" else None', spec)
        self.assertNotIn("console=False", spec)

        main = (ROOT / "desktop" / "src-tauri" / "src" / "main.rs").read_text(
            encoding="utf-8"
        )
        lifecycle = (
            ROOT / "desktop" / "src-tauri" / "src" / "lifecycle.rs"
        ).read_text(encoding="utf-8")
        self.assertIn('windows_subsystem = "windows"', main)
        self.assertIn("CREATE_NO_WINDOW", lifecycle)
        self.assertIn("command.creation_flags(CREATE_NO_WINDOW)", lifecycle)

        shared_app = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW', shared_app)
        self.assertGreaterEqual(shared_app.count("**_background_process_kwargs()"), 3)

    def test_windows_installer_has_canonical_branding_and_optional_cuda_page(self) -> None:
        overlay = (
            ROOT / "desktop" / "src-tauri" / "tauri.windows.conf.json"
        ).read_text(encoding="utf-8")
        hooks = (
            ROOT
            / "desktop"
            / "src-tauri"
            / "installer"
            / "windows"
            / "installer-hooks.nsh"
        ).read_text(encoding="utf-8")
        self.assertIn('"headerImage": "installer/windows/header.bmp"', overlay)
        self.assertIn('"sidebarImage": "installer/windows/sidebar.bmp"', overlay)
        self.assertIn('"installerHooks": "installer/windows/installer-hooks.nsh"', overlay)
        self.assertIn('"installerIcon": "installer/windows/installer-icon.ico"', overlay)
        self.assertIn("Install optional NVIDIA CUDA acceleration", hooks)
        self.assertIn("--install-windows-cuda-runtime", hooks)
        self.assertIn("cuda-install-requested.flag", hooks)
        self.assertIn("cuda-installer-handoff.log", hooks)
        self.assertIn('IfFileExists "$APPDATA\\Church Cap\\data\\cuda-install-requested.flag" 0 ChurchCapCudaDone', hooks)
        self.assertLess(hooks.index("cuda-install-requested.flag"), hooks.index("!macro NSIS_HOOK_POSTINSTALL"))
        self.assertIn("cublasLt64_12.dll", hooks)
        self.assertIn("MUI_WELCOMEFINISHPAGE_BITMAP_STRETCH AspectFitHeight", hooks)

        installer_dir = ROOT / "desktop" / "src-tauri" / "installer" / "windows"
        header = (installer_dir / "header.bmp").read_bytes()
        sidebar = (installer_dir / "sidebar.bmp").read_bytes()
        self.assertEqual(struct.unpack_from("<ii", header, 18), (450, 171))
        self.assertEqual(struct.unpack_from("<ii", sidebar, 18), (492, 942))

        icon = (installer_dir / "installer-icon.ico").read_bytes()
        icon_count = struct.unpack_from("<H", icon, 4)[0]
        self.assertGreaterEqual(icon_count, 8)
        for index in range(icon_count):
            image_offset = struct.unpack_from("<I", icon, 18 + (index * 16))[0]
            self.assertNotEqual(icon[image_offset : image_offset + 8], b"\x89PNG\r\n\x1a\n")

        shared_app = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('CUDA_RUNTIME_REQUEST_MARKER = "cuda-install-requested.flag"', shared_app)
        self.assertIn("await asyncio.to_thread(start_cuda_runtime_install)", shared_app)
        self.assertIn("_windows_cuda_runtime_files_ready()", shared_app)
        self.assertIn('origin="installer first-launch retry"', shared_app)

        branding = (ROOT / "scripts" / "release" / "generate-windows-installer-branding.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("church-cap-installer-sidebar-background.png", branding)
        self.assertIn("$Graphics.DrawImage($SidebarBackground, $Area)", branding)
        self.assertNotIn("Add-RadialGlow", branding)
        self.assertNotIn("FromArgb(110, 231, 168)", branding)
        self.assertTrue(
            (ROOT / "assets" / "branding" / "church-cap-installer-sidebar-background.png").is_file()
        )

    def test_common_wrapper_configuration_keeps_platform_resources_external(self) -> None:
        common_config = (
            ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
        ).read_text(encoding="utf-8")
        self.assertIn('"resources": []', common_config)
        self.assertNotIn("engine-macos-arm64", common_config)
        self.assertNotIn("engine-windows-x64", common_config)

    def test_public_updater_key_is_committable_without_weakening_secret_scan(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        workflow = (
            ROOT / ".github" / "workflows" / "python-check.yml"
        ).read_text(encoding="utf-8")
        public_key_path = "packaging/updater/church-cap-updater-public.key"
        self.assertIn(f"!{public_key_path}", gitignore)
        self.assertIn(f"-path './{public_key_path}' -prune", workflow)
        self.assertIn("pip install -r requirements-packaged.txt", workflow)
        self.assertIn("pip-audit --requirement requirements-packaged.txt", workflow)

    def test_windows_overlay_maps_only_the_native_engine_bundle(self) -> None:
        windows_config = (
            ROOT / "desktop" / "src-tauri" / "tauri.windows.conf.json"
        ).read_text(encoding="utf-8")
        self.assertIn("../../dist/engine-windows-x64/church-cap-engine/", windows_config)
        self.assertIn('"engine/church-cap-engine/"', windows_config)
        self.assertNotIn('"app/"', windows_config)


if __name__ == "__main__":
    unittest.main()

import ast
import pathlib
import unittest


class DiagnosticsSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = pathlib.Path("app/main.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        for node in cls.tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "diagnostics_payload":
                cls.payload_source = ast.get_source_segment(cls.source, node) or ""
                break
        else:
            raise AssertionError("diagnostics_payload was not found")

    def test_diagnostics_route_exists(self):
        self.assertIn('"/api/diagnostics/export"', self.source)
        self.assertIn('"/api/diagnostics/download-handoff"', self.source)
        self.assertIn('"/api/download-handoff"', self.source)
        self.assertIn("diagnostics_payload", self.source)
        self.assertIn('"/api/diagnostics/reset-service-metrics"', self.source)
        self.assertIn('"/api/diagnostics/service-report"', self.source)
        self.assertIn('"/api/diagnostics/storage"', self.source)
        self.assertIn('"/api/diagnostics/storage/cleanup"', self.source)

    def test_diagnostics_payload_avoids_transcript_and_secret_sources(self):
        for forbidden in ("settings.operator_password", "settings.session_secret", "hub.final_segments", "segments_to_json", "CONFIG_PATH", "os.environ"):
            self.assertNotIn(forbidden, self.payload_source)

    def test_diagnostics_route_requires_confirmation(self):
        self.assertIn('request.query_params.get("confirmed") != "1"', self.source)
        self.assertIn("confirmation_required", self.source)

    def test_operator_has_diagnostics_menu_section(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        self.assertIn('data-section="diagnostics"', operator)
        self.assertIn('id="operator-section-diagnostics"', operator)
        self.assertIn("/operator#diagnostics", pathlib.Path("app/templates/feedback.html").read_text(encoding="utf-8"))
        self.assertIn("Download anonymised service report", operator)

    def test_diagnostics_public_sharing_warning_exists(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        feedback = pathlib.Path("app/templates/feedback.html").read_text(encoding="utf-8")
        self.assertIn("Do not post the file publicly on GitHub", operator)
        self.assertIn("public or unsecured LAN", operator)
        self.assertIn("diagnosticsDownloadDialog", operator)
        self.assertIn("handleOperatorQrDownload", operator)
        self.assertIn("Share QR", operator)
        self.assertIn("Do not post the file publicly on GitHub", feedback)
        self.assertIn("do not post it publicly on GitHub", self.source)

    def test_cuda_log_path_uses_relative_label(self):
        self.assertIn('CUDA_RUNTIME_LOG_LABEL = "logs/cuda-runtime-install.log"', self.source)
        self.assertNotIn('"log": str(PROJECT_ROOT / "logs" / "cuda-runtime-install.log")', self.source)
        self.assertNotIn('return {"pid": process.pid, "log": str(log_path)}', self.source)

    def test_cuda_runtime_installer_supports_linux(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        self.assertIn('script = PROJECT_ROOT / "install-cuda-runtime-linux.sh"', self.source)
        self.assertIn('command = ["/usr/bin/env", "bash", str(script)]', self.source)
        self.assertIn("platform !== 'windows' && platform !== 'linux'", operator)
        self.assertIn("Install / repair CUDA runtime", operator)

    def test_redaction_helper_exists(self):
        self.assertIn("def _redact_local_paths", self.source)
        self.assertIn("def _redact_diagnostics_value", self.source)
        self.assertIn("return _redact_diagnostics_value(payload)", self.payload_source)
        self.assertIn("<home>", self.source)
        self.assertIn("<project_root>", self.source)

    def test_diagnostics_excludes_audio_device_names(self):
        self.assertIn('if key not in {"audio_device"}', self.payload_source)
        self.assertIn('"metrics": safe_metrics', self.payload_source)
        self.assertNotIn('"metrics": get_metrics()', self.payload_source)

    def test_diagnostics_includes_language_state(self):
        for expected in (
            '"provider": translation.get("provider")',
            '"max_active_languages": translation.get("max_active_languages")',
            '"language_policy": translation.get("language_policy")',
            '"priority_mode": translation.get("priority_mode")',
            '"active_translated_languages": translation.get("active_translated_languages", [])',
            '"viewer_language_counts": translation.get("viewer_languages", {})',
        ):
            self.assertIn(expected, self.payload_source)

    def test_diagnostics_includes_privacy_safe_retained_service_metrics(self):
        self.assertIn('"diagnostics_schema_version": 2', self.payload_source)
        self.assertIn('"last_service_metrics": get_service_metrics()', self.payload_source)
        self.assertIn('"service_metrics": get_service_metrics_report()', self.payload_source)
        self.assertIn("They exclude audio, transcripts, captions, translations", self.payload_source)

    def test_service_start_seeds_already_connected_viewers(self):
        self.assertIn("record_viewer_counts,", self.source)
        self.assertIn("record_viewer_counts(hub.language_counts())", self.source)

    def test_anonymised_service_report_has_a_separate_allow_listed_route(self):
        self.assertIn("def export_anonymised_service_report", self.source)
        self.assertIn("service_report_payload()", self.source)
        self.assertIn("church-cap-service-report-", self.source)
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        self.assertIn("/api/diagnostics/service-report", operator)
        self.assertIn("service_report", operator)

    def test_reset_measurements_uses_themed_confirmation_dialog(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        self.assertIn('id="resetServiceMeasurementsDialog"', operator)
        self.assertIn('class="service-leader-dialog service-leader-confirm-dialog glass-card"', operator)
        self.assertIn('id="resetServiceMeasurementsConfirm"', operator)
        self.assertIn("service-leader-danger-button", operator)
        self.assertIn("confirmResetServiceMeasurements", operator)
        self.assertIn("dialog.showModal();", operator)
        self.assertNotIn("window.confirm('Reset all retained test measurements", operator)

    def test_storage_use_is_inside_diagnostics_and_uses_themed_cleanup_dialog(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        diagnostics_start = operator.index('id="operator-section-diagnostics"')
        updates_start = operator.index('id="operator-section-updates"')
        diagnostics_section = operator[diagnostics_start:updates_start]
        self.assertIn("Application storage", diagnostics_section)
        self.assertIn('id="storageUseTotal"', diagnostics_section)
        self.assertIn('id="storageCleanupDialog"', operator)
        self.assertIn('id="storageCleanupConfirm"', operator)
        self.assertIn("MAX_BENCHMARK_SAMPLES", operator)

    def test_translated_audio_installer_is_visible_bounded_and_service_safe(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        languages_start = operator.index('id="operator-section-languages"')
        audience_start = operator.index('id="operator-section-audience"')
        languages_section = operator[languages_start:audience_start]
        diagnostics_start = operator.index('id="operator-section-diagnostics"')
        updates_start = operator.index('id="operator-section-updates"')
        diagnostics_section = operator[diagnostics_start:updates_start]
        self.assertIn("Spoken translated audio", languages_section)
        self.assertIn('id="translatedAudioInstallButton"', languages_section)
        self.assertIn('id="translatedAudioCatalog"', languages_section)
        self.assertIn('id="translatedAudioSelectionSize"', languages_section)
        self.assertIn('id="translatedAudioInstallProgress"', languages_section)
        self.assertIn('class="spoken-audio-install-spinner"', languages_section)
        self.assertIn("Install selected languages", languages_section)
        self.assertIn('id="translatedAudioEnabled"', languages_section)
        self.assertNotIn('id="translatedAudioInstallButton"', diagnostics_section)
        self.assertIn("/api/translated-audio/install", operator)
        self.assertIn('@app.post("/api/translated-audio/install")', self.source)
        self.assertIn("if captions_are_running():", self.source)
        self.assertIn("Stop captions before installing translated audio", self.source)
        self.assertIn("normalise_voice_package_selection", self.source)
        self.assertIn('body.get("packages")', self.source)
        self.assertIn("tts_install_state()", self.payload_source)
        self.assertIn("renderTranslatedAudioInstallProgress('starting'", operator)
        self.assertIn("renderTranslatedAudioInstallProgress('installing'", operator)
        self.assertIn("renderTranslatedAudioInstallProgress('error'", operator)
        self.assertIn("Stop captions to install", operator)
        self.assertIn("button.dataset.captionsRunning", operator)
        self.assertIn("data.performance_locked === true", operator)
        self.assertIn('id="translatedAudioRemoveButton"', languages_section)
        self.assertIn('id="translatedAudioRemoveDialog"', operator)
        self.assertIn("openTranslatedAudioRemoveDialog", operator)
        self.assertIn("confirmTranslatedAudioRemoval", operator)
        self.assertIn("/api/translated-audio/uninstall", operator)
        self.assertIn('@app.post("/api/translated-audio/uninstall")', self.source)
        uninstall_route = self.source.split('@app.post("/api/translated-audio/uninstall")', 1)[1].split('@app.post("/api/translation/install")', 1)[0]
        self.assertIn("Depends(require_operator)", uninstall_route)
        self.assertIn("if captions_are_running():", uninstall_route)
        self.assertIn('body.get("confirmed") is not True', uninstall_route)
        self.assertIn("uninstall_reviewed_voice_packages", uninstall_route)
        self.assertIn("await hub.broadcast_viewer_meta()", uninstall_route)
        self.assertIn('id="diagnosticsSpokenAudioTotal"', diagnostics_section)
        self.assertIn('id="diagnosticsSpokenAudioList"', diagnostics_section)
        self.assertIn('id="diagnosticsTranslatedAudioRemoveButton"', diagnostics_section)
        self.assertIn("renderDiagnosticsSpokenAudioStorage", operator)
        self.assertIn('"spoken_audio": _spoken_audio_models_snapshot(app_support)', pathlib.Path("app/storage.py").read_text(encoding="utf-8"))

    def test_translated_audio_language_toggle_is_authenticated_and_persistent(self):
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        runtime = pathlib.Path("app/runtime_config.py").read_text(encoding="utf-8")
        speech = pathlib.Path("app/tts.py").read_text(encoding="utf-8")
        broadcast = pathlib.Path("app/broadcast.py").read_text(encoding="utf-8")
        client = pathlib.Path("app/static/client.js").read_text(encoding="utf-8")

        self.assertIn('id="translatedAudioEnabled"', operator)
        languages_start = operator.index('id="operator-section-languages"')
        translated_audio_toggle = operator.index('id="translatedAudioEnabled"')
        self.assertGreater(translated_audio_toggle, languages_start)
        self.assertIn('class="toggle-row language-speech-toggle"', operator)
        self.assertNotIn("dashboard-speech-toggle", operator)
        self.assertIn("saveTranslatedAudioSetting(this)", operator)
        self.assertIn("/api/translated-audio/settings", operator)
        self.assertIn('@app.post("/api/translated-audio/settings")', self.source)
        route = self.source.split('@app.post("/api/translated-audio/settings")', 1)[1].split('@app.post("/api/translation")', 1)[0]
        self.assertIn("Depends(require_operator)", route)
        self.assertIn("set_translated_audio_config", route)
        self.assertIn("await hub.broadcast_viewer_meta()", route)
        self.assertIn('"translated_audio_enabled": True', runtime)
        self.assertIn("def set_translated_audio_config", runtime)
        self.assertIn("def set_operator_enabled", speech)
        self.assertIn("async def broadcast_viewer_meta", broadcast)
        self.assertIn("|| !operatorEnabled", client)

    def test_system_specs_are_included(self):
        self.assertIn("def _system_specs_snapshot", self.source)
        self.assertIn("total_memory_gib", self.source)
        self.assertIn("project_drive_free_gib", self.source)
        self.assertIn('"system": _system_specs_snapshot()', self.payload_source)

    def test_tigrinya_text_model_is_in_recommended_bundle_pinned_and_licensed(self):
        i18n = pathlib.Path("app/i18n.py").read_text(encoding="utf-8")
        operator = pathlib.Path("app/templates/operator.html").read_text(encoding="utf-8")
        notices = pathlib.Path("docs/legal/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        installer = pathlib.Path("scripts/install-opus-tigrinya-ct2-int8.sh").read_text(encoding="utf-8")
        windows_installer = pathlib.Path("scripts/install-opus-tigrinya-ct2-int8.ps1").read_text(encoding="utf-8")
        recommended_installer = pathlib.Path("scripts/install-small100-ct2-int8.sh").read_text(encoding="utf-8")

        self.assertIn('"code": "ti"', i18n)
        self.assertIn('Helsinki-NLP/opus-mt-en-ti', i18n)
        self.assertIn('72f1e40b4b60ff4863407f90792b4fac517562ec', installer)
        self.assertIn('id="translationRecommendedInstallButton"', operator)
        self.assertNotIn('id="tigrinyaTranslationInstallButton"', operator)
        self.assertIn("Recommended language bundle", operator)
        self.assertIn("install-opus-tigrinya-ct2-int8.sh", recommended_installer)
        self.assertIn("failed its local translation check", installer)
        self.assertIn("WriteAllText", windows_installer)
        self.assertIn("UTF8Encoding", windows_installer)
        self.assertIn("Remove-Item -LiteralPath $TempPythonScript", windows_installer)
        self.assertNotIn("& $Python -c $Code", windows_installer)
        self.assertIn('id="translationPrimaryResult"', operator)
        self.assertIn("setTranslationSaveButtonsBusy", operator)
        self.assertIn("tigrinyaReadinessChanged", operator)
        self.assertIn("if (tigrinyaReadinessChanged) filterOperatorLanguages();", operator)
        self.assertIn("Tigrinya is not ready yet.", operator)
        self.assertIn("'Installing the Recommended language bundle'", operator)
        self.assertNotIn("'Installing the Recommended language bundle, including Tigrinya'", operator)
        self.assertIn("resources.opus_tigrinya?.status?.ready", pathlib.Path("app/static/client.js").read_text(encoding="utf-8"))
        self.assertIn("Apache-2.0", notices)


if __name__ == "__main__":
    unittest.main()

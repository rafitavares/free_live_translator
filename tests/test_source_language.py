"""Testes do fork: língua de origem configurável (padrão português).

A suíte herdada do Church Cap assume inglês e roda com CAPTION_SOURCE_LANGUAGE=en.
Estes testes rodam num subprocesso com a língua definida explicitamente, porque
SOURCE_LANGUAGE é lido na importação.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_probe(code: str, language: str | None, cwd: Path | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "CAPTION_SOURCE_LANGUAGE"}
    if language is not None:
        env["CAPTION_SOURCE_LANGUAGE"] = language
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=str(cwd or ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1])


SOURCE_PROBE = """
import json
from app.source_language import SOURCE_LANGUAGE, whisper_model_for_source, default_initial_prompt
from app import i18n
print(json.dumps({
    "source": SOURCE_LANGUAGE,
    "i18n_source": i18n.SOURCE_LANGUAGE,
    "translator_source": i18n.LocalTranslator().source_language,
    "base": whisper_model_for_source("base.en"),
    "medium": whisper_model_for_source("medium.en"),
    "prompt": default_initial_prompt(),
}))
"""


class SourceLanguageTests(unittest.TestCase):
    def test_default_is_portuguese_with_multilingual_models(self):
        with tempfile.TemporaryDirectory() as empty_dir:  # sem .env
            data = run_probe(SOURCE_PROBE, None, cwd=Path(empty_dir))
        self.assertEqual(data["source"], "pt")
        self.assertEqual(data["i18n_source"], "pt")
        self.assertEqual(data["translator_source"], "pt")
        self.assertEqual(data["base"], "base")
        self.assertEqual(data["medium"], "medium")
        self.assertIn("Kardec", data["prompt"])

    def test_english_keeps_english_only_models(self):
        data = run_probe(SOURCE_PROBE, "en")
        self.assertEqual(data["source"], "en")
        self.assertEqual(data["base"], "base.en")
        self.assertIn("Church service", data["prompt"])

    def test_region_codes_are_reduced_to_base_language(self):
        data = run_probe(SOURCE_PROBE, "pt_BR")
        self.assertEqual(data["source"], "pt")
        data = run_probe(SOURCE_PROBE, "DE-ch")
        self.assertEqual(data["source"], "de")
        self.assertEqual(data["prompt"], "")

    def test_dotenv_value_is_read_when_environment_is_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env").write_text("# exemplo\nCAPTION_SOURCE_LANGUAGE=de\n", encoding="utf-8")
            data = run_probe(SOURCE_PROBE, None, cwd=Path(tmp))
        self.assertEqual(data["source"], "de")

    def test_transcribers_switch_to_multilingual_model_for_portuguese(self):
        code = """
        import json, sys, types
        # Sem PortAudio no ambiente de teste: o construtor não abre áudio.
        sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
        from app.transcription.faster_whisper_live import FasterWhisperTranscriber
        from app.transcription.whisper_live import WhisperLiveTranscriber
        fw = FasterWhisperTranscriber(model_name="small.en")
        ow = WhisperLiveTranscriber(model_name="small.en")
        print(json.dumps({"fw": [fw.model_name, fw.language], "ow": [ow.model_name, ow.language]}))
        """
        data = run_probe(code, "pt")
        self.assertEqual(data["fw"], ["small", "pt"])
        self.assertEqual(data["ow"], ["small", "pt"])

    def test_source_captions_route_to_portuguese_viewers_untranslated(self):
        code = """
        import json
        from app.broadcast import CaptionHub
        from app.models import CaptionSegment
        hub = CaptionHub()
        seg = CaptionSegment(text="Boa noite a todos", is_final=True)
        same = hub._translate_segment_for_language(seg, "pt")
        print(json.dumps({"hub_source": hub.source_language, "same": same is seg}))
        """
        data = run_probe(code, "pt")
        self.assertEqual(data["hub_source"], "pt")
        self.assertTrue(data["same"])

    def test_runtime_config_keeps_source_language_and_multilingual_model(self):
        code = """
        import json, tempfile, os
        from pathlib import Path
        import app.runtime_config as rc
        tmp = Path(tempfile.mkdtemp()) / "runtime.json"
        rc.CONFIG_PATH = tmp
        cfg = rc.save_runtime_config({"whisper_model": "small", "translation_allowed_languages": ["de"]})
        print(json.dumps({"model": cfg.get("whisper_model"), "allowed": cfg.get("translation_allowed_languages")}))
        """
        data = run_probe(code, "pt")
        self.assertEqual(data["model"], "small")
        self.assertIn("pt", data["allowed"])
        self.assertIn("de", data["allowed"])
        self.assertNotIn("en", data["allowed"])


    def test_portuguese_glossary_fixes_common_spiritist_terms(self):
        code = """
        import json
        from pathlib import Path
        from app.glossary import Glossary
        g = Glossary(path=Path("/nao/existe.csv"))
        print(json.dumps({"fixed": g.apply("o peri espírito segundo alan kardec e a desobceção")}))
        """
        data = run_probe(code, "pt")
        self.assertEqual(data["fixed"], "o perispírito segundo Allan Kardec e a desobsessão")

    def test_local_glossary_comment_lines_are_ignored(self):
        code = """
        import json, tempfile
        from pathlib import Path
        from app.glossary import Glossary
        tmp = Path(tempfile.mkdtemp()) / "g.csv"
        tmp.write_text("wrong,correct\\n# exemplo,Exemplo\\ncasa luz,Casa Luz\\n", encoding="utf-8")
        g = Glossary(path=tmp)
        print(json.dumps({"comment": g.apply("# exemplo"), "row": g.apply("na casa luz")}))
        """
        data = run_probe(code, "pt")
        self.assertEqual(data["comment"], "# exemplo")
        self.assertEqual(data["row"], "na Casa Luz")


    def test_simple_panel_requires_login_and_renders_portuguese(self):
        code = """
        import json, sys, types, tempfile, os
        sys.modules.setdefault("sounddevice", types.ModuleType("sounddevice"))
        os.environ["CHURCH_CAP_DATA_DIR"] = tempfile.mkdtemp()
        from fastapi.testclient import TestClient
        import app.main as m
        c = TestClient(m.app, base_url="http://localhost:9090")
        anon = c.get("/simples", follow_redirects=False)
        m.app.dependency_overrides[m.require_operator] = lambda: None
        page = c.get("/simples")
        print(json.dumps({"anon": anon.status_code, "ok": page.status_code,
                          "pt": "Iniciar tradução" in page.text and '"pt"' in page.text}))
        """
        data = run_probe(code, "pt")
        self.assertEqual(data["anon"], 303)
        self.assertEqual(data["ok"], 200)
        self.assertTrue(data["pt"])


if __name__ == "__main__":
    unittest.main()

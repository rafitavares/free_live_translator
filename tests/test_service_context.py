import unittest

from app.bible_references import find_bible_references, format_bible_references
from app.context_prompt import MAX_SERVICE_RECOGNITION_HINTS, build_context_prompt
from app.service_context import ServiceContextManager
from app.service_context_extractor import (
    MAX_UPLOAD_BYTES,
    ServiceContextInputError,
    decode_uploaded_notes,
    extract_service_context,
    normalise_notes,
)


class BibleReferenceTests(unittest.TestCase):
    def test_finds_canonical_and_spoken_references_without_duplicates(self):
        references = find_bible_references(
            "Read John 3:16-18, then First Corinthians chapter 13 verses 4-7. John 3:16-18 again."
        )
        self.assertEqual([item.canonical for item in references], ["John 3:16-18", "1 Corinthians 13:4-7"])
        self.assertIn("chapter 3", references[0].spoken)
        self.assertIn("verses 16 to 18", references[0].spoken)

    def test_formats_spoken_reference_without_service_notes(self):
        self.assertEqual(
            format_bible_references("first Corinthians chapter thirteen verse four"),
            "1 Corinthians 13:4",
        )

    def test_formats_spoken_ranges_and_large_psalm_numbers(self):
        self.assertEqual(
            format_bible_references(
                "Read John chapter three verses sixteen to eighteen, then "
                "Psalm chapter one hundred and nineteen verse one hundred and five."
            ),
            "Read John 3:16-18, then Psalms 119:105.",
        )

    def test_formatter_requires_a_reference_shape(self):
        ordinary = (
            "John marked chapter four as complete, mark 5 items on the form, "
            "and First Corinthians was a manuscript title."
        )
        self.assertEqual(format_bible_references(ordinary), ordinary)

    def test_numeric_ambiguous_book_is_formatted_when_reference_is_explicit(self):
        self.assertEqual(format_bible_references("Please read mark 5:2."), "Please read Mark 5:2.")

    def test_spoken_references_are_discovered_during_note_analysis(self):
        references = find_bible_references("Read Habakkuk chapter two verse four.")
        self.assertEqual([item.canonical for item in references], ["Habakkuk 2:4"])


class ServiceContextInputTests(unittest.TestCase):
    def test_accepts_utf8_text_and_normalises_lines(self):
        text = decode_uploaded_notes(b"Title: God\xe2\x80\x99s Faithfulness\r\nJohn 3:16\r\n", "notes.md")
        self.assertEqual(normalise_notes(text), "Title: God’s Faithfulness\nJohn 3:16")

    def test_rejects_unsupported_binary_and_oversized_files(self):
        with self.assertRaises(ServiceContextInputError):
            decode_uploaded_notes(b"%PDF-1.7", "notes.pdf")
        with self.assertRaises(ServiceContextInputError):
            decode_uploaded_notes(b"x" * (MAX_UPLOAD_BYTES + 1), "notes.txt")

    def test_full_script_extracts_distinctive_terms_and_references(self):
        script = """
        Theme: Faithfulness in Exile
        Today Nebuchadnezzar challenges Daniel. Nebuchadnezzar builds an image,
        but Nebuchadnezzar cannot command faithful worship. Read Daniel 3:16-18.
        """
        result = extract_service_context(script)
        self.assertIn("Daniel 3:16-18", [item.canonical for item in result.references])
        self.assertIn("nebuchadnezzar", [item.text.casefold() for item in result.terms])
        self.assertLessEqual(len(result.terms), 120)


class ContextPromptTests(unittest.TestCase):
    def test_budget_omits_whole_entries_and_does_not_truncate_them(self):
        bundle = build_context_prompt(
            "Church audio.",
            ["Nebuchadnezzar", "Mephibosheth", "A deliberately very long final phrase"],
            ["John, chapter 3, verses 16 to 18"],
            max_tokens=11,
            token_count=lambda value: len(value.split()),
        )
        self.assertTrue(bundle.included)
        self.assertTrue(bundle.omitted)
        for item in bundle.included:
            self.assertIn(item, bundle.initial_prompt)
        for item in bundle.omitted:
            self.assertNotIn(item, bundle.initial_prompt)

    def test_hotwords_include_terms_and_only_difficult_book_names(self):
        bundle = build_context_prompt(
            "Church audio.",
            ["Nebuchadnezzar"],
            ["Daniel 3:16-18", "Habakkuk 2:4"],
            max_tokens=30,
            token_count=lambda value: len(value.split()),
        )
        self.assertEqual(bundle.hotwords, "Nebuchadnezzar, Habakkuk")
        self.assertNotIn("chapter", bundle.initial_prompt.casefold())
        self.assertNotIn("Daniel", bundle.initial_prompt)

    def test_service_recognition_hints_are_capped(self):
        terms = [f"DistinctiveName{index}" for index in range(20)]
        bundle = build_context_prompt(
            "Church audio.",
            terms,
            [],
            max_tokens=500,
            token_count=lambda value: len(value.split()),
        )
        self.assertEqual(len(bundle.included), MAX_SERVICE_RECOGNITION_HINTS)
        self.assertEqual(len(bundle.omitted), 18)


class ServiceContextLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.now = 1_000.0
        self.manager = ServiceContextManager(clock=lambda: self.now)

    def _prepare(self):
        state = self.manager.analyse(
            "Theme: Faithfulness in Exile\nNebuchadnezzar appears three times. "
            "Nebuchadnezzar speaks. Nebuchadnezzar listens. Daniel 3:16-18.",
            source_summary="Pasted service notes",
        )
        self.assertEqual(state["state"], "review")
        return self.manager.approve(
            {
                "terms": [{"text": "Nebuchadnezzar"}],
                "references": [{"canonical": "Daniel 3:16-18", "spoken": "Daniel, chapter 3, verses 16 to 18"}],
                "corrections": [{"heard_as": "never could net sir", "replace_with": "Nebuchadnezzar"}],
            },
            base_prompt="Church service audio.",
        )

    def test_approved_context_locks_and_becomes_inactive_after_service(self):
        ready = self._prepare()
        self.assertEqual(ready["state"], "ready")
        snapshot = self.manager.lock_for_service()
        self.assertIsNotNone(snapshot)
        self.assertEqual(self.manager.public_state()["state"], "locked")
        self.manager.finish_service()
        state = self.manager.public_state()
        self.assertEqual(state["state"], "inactive")
        self.assertFalse(state["active_for_service"])
        self.assertEqual(state["included_count"], ready["included_count"])
        self.assertEqual(state["inactive_seconds_remaining"], 4 * 60 * 60)

    def test_inactive_context_requires_explicit_rearm_and_expires(self):
        self._prepare()
        self.manager.lock_for_service()
        self.manager.finish_service()
        self.assertIsNone(self.manager.lock_for_service())
        self.assertEqual(self.manager.rearm(base_prompt="Church service audio.")["state"], "ready")
        self.manager.lock_for_service()
        self.manager.finish_service()
        self.now += 4 * 60 * 60 + 1
        self.assertEqual(self.manager.public_state()["state"], "empty")

    def test_session_corrections_are_non_cascading_and_only_apply_while_locked(self):
        self._prepare()
        self.assertEqual(self.manager.apply_corrections("never could net sir"), "never could net sir")
        self.manager.lock_for_service()
        self.assertEqual(self.manager.apply_corrections("Never Could Net Sir spoke"), "Nebuchadnezzar spoke")
        self.manager.finish_service()
        self.assertEqual(self.manager.apply_corrections("never could net sir"), "never could net sir")

    def test_session_correction_matcher_is_precompiled_once(self):
        self._prepare()
        snapshot = self.manager.lock_for_service()
        matcher = snapshot.correction_matcher
        self.manager.apply_corrections("never could net sir")
        self.manager.apply_corrections("never could net sir")
        self.assertIs(self.manager.active_snapshot().correction_matcher, matcher)

    def test_analysis_selects_only_the_ranked_hint_shortlist(self):
        text = "\n".join(
            f"DistinctiveName{index} DistinctiveName{index} DistinctiveName{index}"
            for index in range(20)
        )
        state = self.manager.analyse(text, source_summary="Pasted service notes")
        self.assertEqual(sum(1 for item in state["terms"] if item["selected"]), 0)
        self.assertFalse(state["recognition_assistance_enabled"])

    def test_safe_default_keeps_service_terms_out_of_whisper(self):
        self._prepare()
        snapshot = self.manager.lock_for_service()
        self.assertFalse(snapshot.recognition_assistance_enabled)
        self.assertEqual(snapshot.recognition_mode, "corrections_only")
        self.assertIsNone(snapshot.hotwords)
        self.assertEqual(snapshot.included_count, 0)
        self.assertEqual(snapshot.additional_prompt_token_count, 0)

    def test_experimental_assistance_is_explicit_and_tightly_bounded(self):
        self.manager.analyse("A usable service context", source_summary="Pasted service notes")
        state = self.manager.approve(
            {
                "recognition_assistance_enabled": True,
                "terms": [
                    {"text": f"DistinctiveName{index}", "selected": True}
                    for index in range(20)
                ],
            },
            base_prompt="Church audio.",
        )
        self.assertTrue(state["recognition_assistance_enabled"])
        self.assertEqual(state["recognition_mode"], "experimental_hints")
        self.assertLessEqual(state["included_count"], MAX_SERVICE_RECOGNITION_HINTS)
        self.assertLessEqual(state["additional_prompt_token_count"], 8)
        self.assertEqual(sum(1 for item in state["terms"] if item["selected"]), MAX_SERVICE_RECOGNITION_HINTS)

    def test_approval_endpoint_enforces_the_hint_limit(self):
        self.manager.analyse("A usable service context", source_summary="Pasted service notes")
        state = self.manager.approve(
            {
                "recognition_assistance_enabled": True,
                "terms": [
                    {"text": f"DistinctiveName{index}", "selected": True}
                    for index in range(20)
                ],
            },
            base_prompt="Church audio.",
        )
        self.assertEqual(len(state["terms"]), 20)
        self.assertEqual(sum(1 for item in state["terms"] if item["selected"]), MAX_SERVICE_RECOGNITION_HINTS)
        self.assertLessEqual(state["included_count"], MAX_SERVICE_RECOGNITION_HINTS)

    def test_public_state_never_contains_raw_notes_or_prompt_text(self):
        raw = "this private full script sentence must never be retained after analysis. John 3:16"
        self.manager.analyse(raw, source_summary="Pasted service notes")
        public = str(self.manager.public_state())
        self.assertNotIn("this private full script sentence must never be retained", public)
        self.assertNotIn("initial_prompt", public)


class OperatorServiceContextSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        cls.main = Path("app/main.py").read_text(encoding="utf-8")
        cls.operator = Path("app/templates/operator.html").read_text(encoding="utf-8")

    def test_dashboard_exposes_optional_pre_service_submenu(self):
        self.assertIn('data-subsection="service-context"', self.operator)
        self.assertIn("Before the service · optional", self.operator)
        self.assertIn("service-context-nav-tags", self.operator)
        self.assertIn("service-context-info-button", self.operator)
        self.assertIn('id="serviceContextInformationDialog"', self.operator)
        self.assertIn("Service Context · Beta · Optional", self.operator)
        self.assertIn("may increase processing load, caption latency, or unstable wording", self.operator)
        self.assertIn("compare accuracy and delay with it switched off", self.operator)
        self.assertIn("Experimental recognition assistance", self.operator)
        self.assertIn("Off by default", self.operator)
        self.assertIn("Notes stay on this device", self.operator)
        self.assertLess(self.operator.index('data-subsection="service-context"'), self.operator.index('data-subsection="performance"'))

    def test_mutating_routes_apply_operator_request_protection(self):
        route_block = self.main.split('@app.post("/api/service-context/analyse")', 1)[1].split('@app.post("/api/start")', 1)[0]
        self.assertGreaterEqual(route_block.count("require_operator_mutation(request)"), 5)
        self.assertIn('@app.delete("/api/service-context")', route_block)

    def test_transcription_uses_context_before_local_glossary(self):
        self.assertIn("context_corrected = service_context.apply_corrections(segment.text)", self.main)
        self.assertIn("glossary_corrected = glossary.apply(context_corrected)", self.main)
        self.assertIn("reference_corrected = format_bible_references(glossary_corrected)", self.main)
        self.assertIn("corrected = profanity_filter.apply(reference_corrected, enabled=filter_enabled)", self.main)

    def test_faster_whisper_does_not_duplicate_context_in_initial_prompt(self):
        self.assertIn('if active_context and active_context.recognition_assistance_enabled and mode != "faster_whisper":', self.main)
        self.assertIn("initial_prompt = active_context.initial_prompt", self.main)
        self.assertIn("initial_prompt=initial_prompt", self.main)
        self.assertIn("if active_context and active_context.recognition_assistance_enabled", self.main)
        self.assertIn("service_context_mode", self.main)


if __name__ == "__main__":
    unittest.main()

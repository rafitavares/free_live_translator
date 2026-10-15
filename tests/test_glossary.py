import tempfile
import unittest
from unittest import mock
from pathlib import Path

from app.context_prompt import _default_token_count
from app.glossary import Glossary


class ChristianGlossaryTests(unittest.TestCase):
    def setUp(self):
        self.glossary = Glossary(path=Path("/path/that/does/not/exist.csv"))

    def test_builtin_corrections_cover_distinctive_christian_terms(self):
        text = "Thesalonians mentions Nebuchadnezzer and Melchizadek."
        self.assertEqual(
            self.glossary.apply(text),
            "Thessalonians mentions Nebuchadnezzar and Melchizedek.",
        )

    def test_ambiguous_book_correction_requires_reference_context(self):
        self.assertEqual(
            self.glossary.apply("The new workflow improved efficiency for everyone."),
            "The new workflow improved efficiency for everyone.",
        )
        self.assertEqual(
            self.glossary.apply("This chapter explains efficiency in administration."),
            "This chapter explains efficiency in administration.",
        )
        self.assertEqual(
            self.glossary.apply("Please turn to Efficiency chapter two."),
            "Please turn to Ephesians chapter two.",
        )

    def test_builtin_phrase_casing_is_applied(self):
        self.assertEqual(
            self.glossary.apply("The holy spirit points us to jesus christ."),
            "The Holy Spirit points us to Jesus Christ.",
        )

    def test_local_rule_overrides_builtin_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / "glossary.csv"
            local.write_text("wrong,correct\nEphushuns,Ephesians Church\n", encoding="utf-8")
            glossary = Glossary(path=local)
            self.assertEqual(glossary.apply("Ephushuns"), "Ephesians Church")

    def test_replacements_are_longest_match_and_non_cascading(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / "glossary.csv"
            local.write_text(
                "wrong,correct\nHoly,Hallowed\nHoly Spirit,Spirit of God\nSpirit of God,Changed twice\n",
                encoding="utf-8",
            )
            glossary = Glossary(path=local, builtin_path=Path(folder) / "missing.csv")
            self.assertEqual(glossary.apply("Holy Spirit"), "Spirit of God")

    def test_legacy_shipped_rows_do_not_restore_unsafe_broad_rules(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / "glossary.csv"
            local.write_text("wrong,correct\nEfficiency,Ephesians\n", encoding="utf-8")
            glossary = Glossary(path=local)
            self.assertEqual(glossary.apply("Operational efficiency matters."), "Operational efficiency matters.")

    def test_prompt_adds_bounded_christian_recognition_context(self):
        prompt = self.glossary.initial_prompt("Church service audio.", max_tokens=60)
        self.assertIn("Nebuchadnezzar", prompt)
        self.assertIn("Messiah", prompt)
        self.assertIn("Deuteronomy", prompt)
        self.assertIn("Great Commission", prompt)
        self.assertLessEqual(_default_token_count(prompt), 60)

    def test_default_prompt_reserves_space_for_core_theology(self):
        prompt = self.glossary.initial_prompt(
            "Church service audio with prayer, Bible readings, worship, sermon, Scripture, "
            "Jesus Christ, Holy Spirit, Psalm, Psalms, Ephesians, Corinthians, Thessalonians."
        )
        self.assertIn("Messiah", prompt)
        self.assertLessEqual(_default_token_count(prompt), 68)

    def test_prompt_skips_oversized_entry_and_uses_shorter_later_term(self):
        with tempfile.TemporaryDirectory() as folder:
            terms = Path(folder) / "terms.txt"
            terms.write_text(
                "theology|100|A deliberately enormous theological expression with many repeated "
                "specialised words that cannot possibly fit inside this exceptionally tiny prompt budget\n"
                "theology|90|grace\n"
                "biblical_names|100|Paul\n"
                "bible_books_places|100|Rome\n"
                "christian_phrases|100|Amen\n",
                encoding="utf-8",
            )
            glossary = Glossary(
                path=Path(folder) / "missing.csv",
                builtin_path=Path(folder) / "missing-builtins.csv",
                prompt_terms_path=terms,
            )
            prompt = glossary.initial_prompt("Church audio.", max_tokens=16)
            self.assertNotIn("enormous theological expression", prompt)
            self.assertIn("grace", prompt)

    def test_prompt_budget_does_not_import_a_transcription_backend(self):
        with mock.patch("builtins.__import__", wraps=__import__) as import_module:
            self.glossary.initial_prompt("Church service audio.", max_tokens=60)

        imported_roots = {call.args[0].split(".", 1)[0] for call in import_module.call_args_list}
        self.assertNotIn("whisper", imported_roots)
        self.assertNotIn("numba", imported_roots)


if __name__ == "__main__":
    unittest.main()

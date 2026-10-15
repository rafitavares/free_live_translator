import unittest

from app.profanity_filter import ProfanityFilter


class ProfanityFilterTests(unittest.TestCase):
    def test_masks_standalone_blocked_words(self):
        profanity_filter = ProfanityFilter(extra_words_path="/path/that/does/not/exist.txt")

        self.assertEqual("That was ****.", profanity_filter.apply("That was crap."))

    def test_does_not_mask_inside_larger_words(self):
        profanity_filter = ProfanityFilter(extra_words_path="/path/that/does/not/exist.txt")

        self.assertEqual("Classic passage.", profanity_filter.apply("Classic passage."))

    def test_can_be_disabled(self):
        profanity_filter = ProfanityFilter(extra_words_path="/path/that/does/not/exist.txt")

        self.assertEqual("That was crap.", profanity_filter.apply("That was crap.", enabled=False))

    def test_masks_common_inflections_and_spaced_compounds(self):
        profanity_filter = ProfanityFilter(extra_words_path="/path/that/does/not/exist.txt")

        for phrase in (
            "assholes",
            "bitches",
            "bull shit",
            "dick head",
            "douchebags",
            "fucked",
            "fuck off",
            "mother fuckers",
            "pissed",
            "shitheads",
            "wanking",
            "whores",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual("*" * len(phrase), profanity_filter.apply(phrase))

    def test_keeps_ambiguous_biblical_words_available(self):
        profanity_filter = ProfanityFilter(extra_words_path="/path/that/does/not/exist.txt")
        wording = "The ass carried the load before the cock crowed, and Jesus spoke about hell."

        self.assertEqual(wording, profanity_filter.apply(wording))


if __name__ == "__main__":
    unittest.main()

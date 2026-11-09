import unittest

from typesprint.engine import Config, Round
from typesprint.exercises import DATA, Exercises


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.game = Round(Config(duration=15), "hello world again", clock=self.clock)

    def test_first_character_starts_clock_even_if_wrong(self):
        self.clock.advance(500)
        self.game.tick()
        self.assertIsNone(self.game.started_at)
        self.assertEqual(self.game.remaining(), 15)
        self.game.insert("x")
        self.assertEqual(self.game.started_at, 600)
        self.assertEqual(self.game.attempts, 1)
        self.assertEqual(self.game.score().mistakes, 1)

    def test_non_text_and_empty_deletion_do_not_start_round(self):
        self.assertFalse(self.game.insert(""))
        self.assertFalse(self.game.backspace())
        self.assertIsNone(self.game.started_at)
        self.assertEqual(self.game.attempts, 0)

    def test_input_at_exact_deadline_is_rejected(self):
        self.game.insert("h")
        self.clock.advance(15)
        self.assertFalse(self.game.insert("e"))
        self.assertEqual(self.game.text, "h")
        self.assertEqual(self.game.attempts, 1)
        self.assertTrue(self.game.finished)
        self.assertEqual(self.game.score().elapsed, 15)

    def test_late_tick_uses_deadline_not_callback_time(self):
        self.game.insert("hello")
        self.clock.advance(90)
        self.game.tick()
        self.assertEqual(self.game.score().elapsed, 15)
        self.assertEqual(self.game.score().wpm, 4)
        self.assertFalse(self.game.backspace())

    def test_input_just_before_deadline_counts(self):
        self.game.insert("h")
        self.clock.advance(14.999)
        self.assertTrue(self.game.insert("e"))
        self.assertEqual(self.game.attempts, 2)
        self.assertFalse(self.game.finished)

    def test_correction_keeps_attempt_mistakes_but_improves_final_wpm(self):
        self.game.insert("x")
        self.game.backspace()
        self.clock.advance(10)
        self.game.insert("hello")
        score = self.game.score()
        self.assertEqual(score.mistakes, 1)
        self.assertEqual(score.attempts, 6)
        self.assertEqual(score.correct_attempts, 5)
        self.assertAlmostEqual(score.accuracy, 100 * 5 / 6)
        self.assertEqual(score.correct_characters, 5)
        self.assertEqual(score.wpm, 6)

    def test_final_text_matching_not_lifetime_correct_attempts_drives_wpm(self):
        self.game.insert("hello")
        self.game.backspace()
        self.clock.advance(12)
        self.game.insert("x")
        self.assertEqual(self.game.score().correct_characters, 4)
        self.assertEqual(self.game.score().correct_attempts, 5)
        self.assertEqual(self.game.score().wpm, 4)

    def test_native_selection_replacement_positions(self):
        self.game.insert("hxllo")
        self.game.edit(1, 2, "")
        self.game.edit(1, 1, "e")
        self.assertEqual(self.game.text, "hello")
        self.assertEqual(self.game.score().mistakes, 1)
        self.assertEqual(self.game.score().correct_characters, 5)

    def test_unicode_characters_count_once(self):
        game = Round(Config(category="german"), "äöüß ÄÖÜ", clock=self.clock)
        game.insert("äöüß ÄÖÜ")
        self.assertEqual(game.attempts, 8)
        self.assertEqual(game.score().accuracy, 100)
        self.assertEqual(game.score().correct_characters, 8)

    def test_restart_is_clean_independent_round(self):
        self.game.insert("wrong")
        self.clock.advance(7)
        restarted = Round(self.game.config, self.game.target, clock=self.clock)
        self.assertIsNone(restarted.started_at)
        self.assertEqual(restarted.text, "")
        self.assertEqual(restarted.score().mistakes, 0)
        self.assertEqual(restarted.remaining(), 15)

    def test_practice_finishes_without_timer_and_preserves_code(self):
        target = "def run():\n    return 1"
        game = Round(Config("practice", "python"), target, clock=self.clock)
        game.insert("def run():\n")
        self.clock.advance(3600)
        self.assertFalse(game.tick())
        self.assertIsNone(game.remaining())
        game.insert("    return 1")
        self.assertTrue(game.finished)
        self.assertEqual(game.text, target)
        self.assertEqual(game.score().accuracy, 100)
        self.assertEqual(game.score().elapsed, 3600)

    def test_practice_allows_mistakes_in_completed_passage(self):
        game = Round(Config("practice"), "hello", clock=self.clock)
        game.insert("hxll")
        self.clock.advance(3)
        game.insert("o")
        self.assertTrue(game.finished)
        self.assertEqual(game.score().mistakes, 1)

    def test_timed_rounds_extend_offline_word_supply(self):
        game = Round(Config(), "hi", clock=self.clock, more_words=lambda: "hello " * 120)
        game.insert("hi")
        self.assertGreater(len(game.target), 500)
        self.assertFalse(game.finished)

    def test_empty_target_rejected(self):
        with self.assertRaises(ValueError):
            Round(Config(), "")

    def test_large_insert_extends_as_far_as_needed(self):
        game = Round(Config(), "hi", clock=self.clock, more_words=lambda: "word " * 120)
        game.insert("x" * 4000)
        self.assertGreaterEqual(len(game.target) - len(game.text), 500)

    def test_config_validation(self):
        for args in [("sprint", "english", 9), ("survival", "python", 30), ("other", "english", 30)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Config(*args)

    def test_record_groups(self):
        self.assertEqual(Config("practice", "german", 60).record_duration, 0)
        self.assertEqual(Config("survival", "english", 60).record_duration, 0)
        self.assertEqual(Config("sprint", "english", 60).record_duration, 60)

    def test_all_bundled_exercises_load(self):
        exercises = Exercises()
        for category in DATA["practice"]:
            game = exercises.create(Config("practice", category))
            self.assertTrue(game.target)
            if category in {"python", "typescript"}:
                self.assertIn("\n", game.target)
                self.assertIn("    ", game.target)
        for category in ("english", "german"):
            self.assertGreater(len(exercises.create(Config(category=category)).target), 500)


class SurvivalTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.game = Round(Config("survival"), "one two three four", clock=self.clock)

    def test_starts_with_thirty_seconds(self):
        self.assertEqual(self.game.remaining(), 30)
        self.game.insert("o")
        self.assertEqual(self.game.deadline, 130)

    def test_bonus_requires_correct_word_and_separator(self):
        self.game.insert("one")
        self.assertEqual(self.game.bonus_seconds, 0)
        self.game.insert(" ")
        self.assertEqual(self.game.bonus_seconds, 1)
        self.assertEqual(self.game.deadline, 131)

    def test_typo_word_does_not_earn_bonus(self):
        self.game.insert("oxe ")
        self.assertEqual(self.game.bonus_seconds, 0)
        self.game.edit(1, 2, "")
        self.game.edit(1, 1, "n")
        self.assertEqual(self.game.bonus_seconds, 1)

    def test_retyping_separator_or_whole_word_never_reawards_bonus(self):
        self.game.insert("one ")
        self.game.backspace()
        self.game.insert(" ")
        self.assertEqual(self.game.bonus_seconds, 1)
        self.game.edit(0, len(self.game.text), "")
        self.game.insert("one ")
        self.assertEqual(self.game.bonus_seconds, 1)
        self.game.insert("two ")
        self.assertEqual(self.game.bonus_seconds, 2)

    def test_bonus_cannot_resurrect_dead_round(self):
        self.game.insert("one")
        self.clock.advance(30)
        self.assertFalse(self.game.insert(" "))
        self.assertEqual(self.game.bonus_seconds, 0)
        self.assertTrue(self.game.finished)

    def test_bonus_before_deadline_extends_life(self):
        self.game.insert("one")
        self.clock.advance(29.99)
        self.game.insert(" ")
        self.clock.advance(.02)
        self.assertFalse(self.game.tick())
        self.clock.advance(1)
        self.assertTrue(self.game.tick())
        self.assertEqual(self.game.score().elapsed, 31)

    def test_multiword_insert_awards_each_position(self):
        self.game.insert("one two three ")
        self.assertEqual(self.game.bonus_seconds, 3)
        self.assertEqual(self.game.remaining(), 33)

    def test_wrong_separator_does_not_commit_word(self):
        self.game.insert("oneX")
        self.assertEqual(self.game.bonus_seconds, 0)

    def test_repeated_word_text_earns_for_each_distinct_position(self):
        game = Round(Config("survival"), "one one one next", clock=self.clock)
        game.insert("one one one ")
        self.assertEqual(game.bonus_seconds, 3)


if __name__ == "__main__":
    unittest.main()

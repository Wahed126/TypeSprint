import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from typesprint.engine import Config, Round
from typesprint.storage import Store
from tests.test_engine import Clock


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "data" / "history.sqlite3"
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def score(self, mode="sprint", category="english", duration=15, text="hello"):
        clock = Clock()
        game = Round(Config(mode, category, duration), "hello", clock=clock)
        game.insert(text[0])
        clock.advance(2 if mode == "practice" else duration if mode == "sprint" else 30)
        if mode == "practice":
            game.insert(text[1:])
        else:
            game.tick()
        return game.score()

    def test_completed_session_visible_in_fresh_process_after_relaunch(self):
        score = self.score()
        self.store.save(score)
        self.store.set_many({"font_size": 28, "mode": "survival"})
        code = """from typesprint.storage import Store
import sys
s = Store(sys.argv[1])
rows = s.history('sprint')
assert len(rows) == 1
assert rows[0]['attempts'] == 1
assert rows[0]['elapsed'] == 15
assert s.get('font_size') == '28'
assert s.get('mode') == 'survival'
s.close()
"""
        subprocess.run([sys.executable, "-c", code, str(self.path)], check=True)

    def test_best_is_scoped_to_mode_category_and_sprint_duration(self):
        self.assertTrue(self.store.save(self.score()))
        self.assertFalse(self.store.save(self.score()))
        self.assertIsNone(self.store.best("sprint", "english", 30))
        self.assertIsNone(self.store.best("sprint", "german", 15))
        self.assertIsNone(self.store.best("survival", "english", 0))
        self.assertTrue(self.store.save(self.score(category="german")))
        self.assertTrue(self.store.save(self.score(mode="survival")))
        self.assertTrue(self.store.save(self.score(duration=30)))

    def test_history_filter_and_newest_first(self):
        self.store.save(self.score())
        self.store.save(self.score(mode="practice", category="python"))
        self.store.save(self.score(mode="survival"))
        self.assertEqual([row["mode"] for row in self.store.history()], ["survival", "practice", "sprint"])
        self.assertEqual(len(self.store.history("practice")), 1)
        self.assertEqual(self.store.history("practice")[0]["category"], "python")
        self.assertEqual(len(self.store.history("invalid")), 0)

    def test_personal_best_requires_strict_improvement(self):
        self.assertTrue(self.store.save(self.score(mode="practice", text="hxxxx")))
        self.assertTrue(self.store.save(self.score(mode="practice")))
        self.assertFalse(self.store.save(self.score(mode="practice")))

    def test_settings_update_and_defaults(self):
        self.assertEqual(self.store.get("font_size", "22"), "22")
        self.store.set_many({"font_size": 24})
        self.store.set_many({"font_size": 30})
        self.assertEqual(self.store.get("font_size"), "30")


if __name__ == "__main__":
    unittest.main()

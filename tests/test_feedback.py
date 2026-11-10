"""Both clients use these same examples, including exact coaching boundaries."""
import json
from pathlib import Path
import unittest

from typesprint.engine import Score
from typesprint.feedback import CATALOG, round_feedback

FIXTURES = json.loads((Path(__file__).resolve().parent.parent / 'web/tests/fixtures/feedback.json').read_text())


class FeedbackTests(unittest.TestCase):
    def test_shared_round_examples(self):
        for case in FIXTURES['cases']:
            with self.subTest(case=case['id']):
                score = Score(**(FIXTURES['base'] | case['score']))
                feedback = round_feedback(score)
                self.assertEqual(feedback.key, case['key'])
                self.assertEqual(feedback.tip, case['tip'])
                self.assertEqual(feedback.title, CATALOG['profiles'][case['key']]['title'])
                self.assertTrue(feedback.message)
                self.assertNotIn('{', feedback.message)
                if case['tip'] == 'mistake_load':
                    self.assertIn(str(score.mistakes), feedback.message)
                    self.assertIn(f'{score.elapsed:.1f}', feedback.message)

    def test_examples_cover_every_message_and_advice(self):
        self.assertEqual({case['key'] for case in FIXTURES['cases']}, set(CATALOG['profiles']))
        self.assertEqual({case['tip'] for case in FIXTURES['cases']} - {None}, set(CATALOG['tips']))

"""Encouraging round feedback, independent of GTK and persistence.

Thresholds are game coaching choices, not population skill rankings. Both clients
use the same catalog and fixture cases; code uses gentler pace thresholds.
"""
from dataclasses import dataclass
import json
from pathlib import Path

from .engine import Score

CATALOG = json.loads((Path(__file__).parent / 'data/feedback.json').read_text(encoding='utf-8'))


@dataclass(frozen=True)
class Feedback:
    key: str
    title: str
    message: str
    tip: str | None


def round_feedback(score: Score) -> Feedback:
    rules = CATALOG['thresholds']
    code = score.category in {'python', 'typescript'}
    steady = rules['code_steady_wpm' if code else 'steady_wpm']
    fast = rules['code_fast_wpm' if code else 'fast_wpm']
    pace = 'fast' if score.wpm >= fast else 'steady' if score.wpm >= steady else 'calm'

    if score.attempts == 0 or score.correct_characters == 0:
        key = 'no_matches'
    elif score.elapsed < rules['minimum_elapsed']:
        key = 'quick_sample'
    elif score.attempts < rules['minimum_attempts']:
        key = 'small_sample'
    elif score.accuracy < rules['low_accuracy']:
        key = 'accuracy_reset'
    elif score.accuracy < rules['target_accuracy']:
        key = 'fast_errors' if pace == 'fast' else 'steady_errors'
    elif score.mistakes == 0 and score.accuracy >= rules['high_accuracy']:
        key = 'clean_' + pace
    elif score.accuracy >= rules['high_accuracy']:
        key = 'accurate_' + pace
    else:
        key = 'polish_fast' if pace == 'fast' else 'polish_calm'

    tip = None
    if key not in {'no_matches', 'quick_sample', 'small_sample'}:
        if (score.accuracy < rules['target_accuracy']
                and score.mistakes >= rules['minimum_mistakes']
                and score.mistakes * 60 / score.elapsed >= rules['mistakes_per_minute']):
            tip = 'mistake_load'
        elif code:
            tip = 'code'
        elif score.mode == 'survival' and score.elapsed >= rules['long_elapsed']:
            tip = 'survival_long'
        elif score.elapsed >= rules['long_elapsed']:
            tip = 'long_focus' if score.accuracy >= rules['target_accuracy'] else 'long_practice'
        elif score.mode == 'sprint' and score.accuracy >= rules['high_accuracy'] and score.duration in {15, 30}:
            tip = 'sprint30' if score.duration == 15 else 'sprint60'
        else:
            tip = score.mode if score.mode in {'practice', 'survival'} else 'repeat'

    profile = CATALOG['profiles'][key]
    message = profile['message']
    if tip:
        message += ' ' + CATALOG['tips'][tip].format(mistakes=score.mistakes, elapsed=f'{score.elapsed:.1f}')
    return Feedback(key, profile['title'], message, tip)

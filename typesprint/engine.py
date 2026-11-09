"""Clock-driven typing rules. This module deliberately has no GTK dependency."""
from dataclasses import dataclass
import re
import time
from typing import Callable


@dataclass(frozen=True)
class Config:
    mode: str = "sprint"
    category: str = "english"
    duration: int = 30

    def __post_init__(self):
        if self.mode not in {"sprint", "practice", "survival"}:
            raise ValueError("Unknown mode")
        allowed = {"english", "german", "python", "typescript"} if self.mode == "practice" else {"english", "german"}
        if self.category not in allowed:
            raise ValueError("Category is unavailable in this mode")
        if self.mode == "sprint" and self.duration not in {15, 30, 60}:
            raise ValueError("Sprint duration must be 15, 30 or 60 seconds")

    @property
    def record_duration(self) -> int:
        return self.duration if self.mode == "sprint" else 0


@dataclass(frozen=True)
class Score:
    mode: str
    category: str
    duration: int
    elapsed: float
    correct_characters: int
    correct_attempts: int
    attempts: int
    mistakes: int
    wpm: float
    accuracy: float
    bonus_seconds: int


class Round:
    def __init__(self, config: Config, target: str, *, clock: Callable[[], float] = time.monotonic,
                 more_words: Callable[[], str] | None = None):
        if not target:
            raise ValueError("An exercise must contain text")
        self.config = config
        self.target = target
        self.clock = clock
        self.more_words = more_words
        self.text = ""
        self.started_at: float | None = None
        self.ended_at: float | None = None
        self.attempts = 0
        self.correct_attempts = 0
        self.awarded_words: set[tuple[int, int]] = set()
        self.bonus_seconds = 0
        self._spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", target)]

    @property
    def finished(self) -> bool:
        return self.ended_at is not None

    @property
    def deadline(self) -> float | None:
        if self.started_at is None or self.config.mode == "practice":
            return None
        seconds = self.config.duration if self.config.mode == "sprint" else 30
        return self.started_at + seconds + self.bonus_seconds

    def tick(self, now: float | None = None) -> bool:
        now = self.clock() if now is None else now
        if not self.finished and self.deadline is not None and now >= self.deadline:
            # A late UI callback must never inflate the measured duration.
            self.ended_at = self.deadline
        return self.finished

    def elapsed(self, now: float | None = None) -> float:
        if self.started_at is None:
            return 0.0
        now = self.clock() if now is None else now
        stop = self.ended_at if self.finished else now
        if self.deadline is not None:
            stop = min(stop, self.deadline)
        return max(0.0, stop - self.started_at)

    def remaining(self, now: float | None = None) -> float | None:
        if self.config.mode == "practice":
            return None
        if self.started_at is None:
            return float(self.config.duration if self.config.mode == "sprint" else 30)
        now = self.clock() if now is None else now
        return max(0.0, self.deadline - (self.ended_at if self.finished else now))

    def _extend(self, needed: int):
        if self.config.mode == "practice" or self.more_words is None:
            return
        while len(self.target) - needed < 500:
            extra = self.more_words()
            if not extra:
                raise ValueError("Word source must supply more text")
            self.target += " " + extra
            self._spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", self.target)]

    def edit(self, start: int, end: int, inserted: str) -> bool:
        """Apply a native buffer edit; text insertion attempts are scored once.

        Deletion is unscored. Positions are Unicode code points, as in GtkTextIter.
        At the exact deadline, neither text nor bonuses can change.
        """
        now = self.clock()
        if self.tick(now):
            return False
        if not 0 <= start <= end <= len(self.text):
            raise ValueError("Edit outside the typed text")
        if not inserted and start == end:
            return False
        if inserted and self.started_at is None:
            self.started_at = now
        self._extend(len(self.text) + len(inserted))
        self.attempts += len(inserted)
        self.correct_attempts += sum(
            position < len(self.target) and character == self.target[position]
            for position, character in enumerate(inserted, start)
        )
        self.text = self.text[:start] + inserted + self.text[end:]
        self._extend(len(self.text))
        if self.config.mode == "survival":
            for word_start, word_end in self._spans:
                # Completing the separator commits the word, including for paste.
                if word_end >= len(self.text):
                    break
                key = (word_start, word_end)
                if (key not in self.awarded_words
                        and self.text[word_start:word_end] == self.target[word_start:word_end]
                        and word_end < len(self.target)
                        and self.text[word_end] == self.target[word_end]):
                    self.awarded_words.add(key)
                    self.bonus_seconds += 1
        if self.config.mode == "practice" and len(self.text) >= len(self.target):
            self.ended_at = now
        return True

    def insert(self, text: str) -> bool:
        return self.edit(len(self.text), len(self.text), text)

    def backspace(self) -> bool:
        if not self.text:
            self.tick()
            return False
        return self.edit(len(self.text) - 1, len(self.text), "")

    def score(self, now: float | None = None) -> Score:
        elapsed = self.elapsed(now)
        matched = sum(a == b for a, b in zip(self.text, self.target))
        return Score(
            self.config.mode, self.config.category, self.config.record_duration, elapsed,
            matched, self.correct_attempts, self.attempts, self.attempts - self.correct_attempts,
            (matched / 5 / (elapsed / 60)) if elapsed > 0 else 0.0,
            (100 * self.correct_attempts / self.attempts) if self.attempts else 100.0,
            self.bonus_seconds,
        )

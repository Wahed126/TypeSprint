"""All content is bundled. No network requests are made by the app."""
import json
from pathlib import Path
import random

DATA = json.loads((Path(__file__).parent / "data" / "exercises.json").read_text(encoding="utf-8"))


class Exercises:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def words(self, category, count=180):
        return " ".join(self.rng.choices(DATA["words"][category], k=count))

    def passage(self, category):
        return self.rng.choice(DATA["practice"][category])

    def create(self, config, **kwargs):
        from .engine import Round
        if config.mode == "practice":
            return Round(config, self.passage(config.category), **kwargs)
        return Round(config, self.words(config.category),
                     more_words=lambda: self.words(config.category), **kwargs)

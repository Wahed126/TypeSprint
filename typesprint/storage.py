"""SQLite persistence, shared by the UI and the headless integration tests."""
from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3


def default_path():
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "typesprint" / "typesprint.sqlite3"


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                mode TEXT NOT NULL,
                category TEXT NOT NULL,
                duration INTEGER NOT NULL,
                elapsed REAL NOT NULL,
                correct_characters INTEGER NOT NULL,
                correct_attempts INTEGER NOT NULL,
                attempts INTEGER NOT NULL,
                mistakes INTEGER NOT NULL,
                wpm REAL NOT NULL,
                accuracy REAL NOT NULL,
                bonus_seconds INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_record
                ON sessions(mode, category, duration, wpm);
        """)
        self.db.commit()

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_many(self, values):
        with self.db:
            self.db.executemany("INSERT INTO settings(key, value) VALUES (?, ?) "
                                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                [(key, str(value)) for key, value in values.items()])

    def best(self, mode, category, duration):
        row = self.db.execute("SELECT MAX(wpm) AS best FROM sessions WHERE "
                              "mode=? AND category=? AND duration=?", (mode, category, duration)).fetchone()
        return row["best"]

    def save(self, score):
        """Save exactly one completed score; return whether it beats the prior best."""
        values = asdict(score)
        with self.db:
            previous = self.best(score.mode, score.category, score.duration)
            values["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            columns = ", ".join(values)
            placeholders = ", ".join("?" for _ in values)
            self.db.execute(f"INSERT INTO sessions ({columns}) VALUES ({placeholders})", tuple(values.values()))
        return previous is None or score.wpm > previous

    def history(self, mode=None):
        query = "SELECT * FROM sessions"
        args = ()
        if mode:
            query += " WHERE mode = ?"
            args = (mode,)
        return self.db.execute(query + " ORDER BY id DESC", args).fetchall()

    def close(self):
        self.db.close()

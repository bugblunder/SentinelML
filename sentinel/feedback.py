"""Local SQLite analyst feedback, keyed by event and model revision."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

VERDICTS = ("Needs investigation", "Expected activity", "Confirmed issue")


@contextmanager
def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    try:
        with con:
            con.execute("""CREATE TABLE IF NOT EXISTS feedback (
                event_id TEXT NOT NULL, model_id TEXT NOT NULL, verdict TEXT NOT NULL,
                note TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(event_id, model_id))""")
            yield con
    finally:
        con.close()


def save_feedback(path, event_id, model_id, verdict, note=""):
    if verdict not in VERDICTS:
        raise ValueError("Choose a supported review status.")
    if len(note) > 2000:
        raise ValueError("Notes may contain at most 2,000 characters.")
    with connect(path) as con:
        con.execute(
            """INSERT INTO feedback VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(event_id, model_id) DO UPDATE SET verdict=excluded.verdict,
            note=excluded.note, updated_at=excluded.updated_at""",
            (event_id, model_id, verdict, note, datetime.now(timezone.utc).isoformat()),
        )


def load_feedback(path, model_id):
    with connect(path) as con:
        return pd.read_sql_query(
            "SELECT * FROM feedback WHERE model_id = ? ORDER BY updated_at DESC", con, params=(model_id,)
        )

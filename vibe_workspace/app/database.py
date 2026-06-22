import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "expenses.db"


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                spent_on TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'uncategorized'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_limit (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                amount REAL NOT NULL
            )
            """
        )

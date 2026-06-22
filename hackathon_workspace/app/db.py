import sqlite3
from contextlib import contextmanager

DB_PATH = "expenses.db"


def configure(db_path: str) -> None:
    global DB_PATH
    DB_PATH = db_path


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL
            )
            """
        )


def insert_expense(description: str, amount: float) -> dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (description, amount) VALUES (?, ?)",
            (description, amount),
        )
        return {"id": cur.lastrowid, "description": description, "amount": amount}


def fetch_expenses() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, description, amount FROM expenses ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def delete_expense(expense_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cur.rowcount > 0

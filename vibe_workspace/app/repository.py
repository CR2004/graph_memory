import sqlite3

from app.models import CategorySummary, Expense, ExpenseCreate


def insert_expense(conn: sqlite3.Connection, data: ExpenseCreate) -> Expense:
    cursor = conn.execute(
        "INSERT INTO expenses (description, amount, spent_on, category) VALUES (?, ?, ?, ?)",
        (data.description, data.amount, data.spent_on.isoformat(), data.category),
    )
    return Expense(id=cursor.lastrowid, **data.model_dump())


def select_expenses(conn: sqlite3.Connection) -> list[Expense]:
    rows = conn.execute(
        "SELECT id, description, amount, spent_on, category FROM expenses ORDER BY spent_on DESC, id DESC"
    ).fetchall()
    return [Expense(**dict(row)) for row in rows]


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> bool:
    cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return cursor.rowcount > 0


def upsert_monthly_limit(conn: sqlite3.Connection, amount: float) -> None:
    conn.execute(
        """
        INSERT INTO monthly_limit (id, amount) VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET amount = excluded.amount
        """,
        (amount,),
    )


def select_monthly_limit(conn: sqlite3.Connection) -> float | None:
    row = conn.execute("SELECT amount FROM monthly_limit WHERE id = 1").fetchone()
    return None if row is None else float(row["amount"])


def summarize_by_category(conn: sqlite3.Connection) -> list[CategorySummary]:
    rows = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        GROUP BY category
        ORDER BY category
        """
    ).fetchall()
    return [CategorySummary(category=r["category"], total=r["total"]) for r in rows]

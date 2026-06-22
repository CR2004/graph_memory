from app.database import get_connection
from app.models import Expense, ExpenseCreate


def create(data: ExpenseCreate) -> Expense:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (description, amount, category) VALUES (?, ?, ?)",
            (data.description, data.amount, data.category),
        )
        row = conn.execute(
            "SELECT id, description, amount, category, created_at FROM expenses WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return Expense(**dict(row))


def list_all() -> list[Expense]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, description, amount, category, created_at FROM expenses ORDER BY id"
        ).fetchall()
        return [Expense(**dict(row)) for row in rows]


def delete(expense_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cur.rowcount > 0

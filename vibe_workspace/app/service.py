import sqlite3

from app import repository
from app.models import BudgetStatus, CategorySummary, Expense, ExpenseCreate


class ExpenseNotFoundError(Exception):
    def __init__(self, expense_id: int) -> None:
        self.expense_id = expense_id
        super().__init__(f"Expense {expense_id} not found")


class LimitNotSetError(Exception):
    def __init__(self) -> None:
        super().__init__("Monthly spending limit is not set")


def create_expense(conn: sqlite3.Connection, data: ExpenseCreate) -> Expense:
    return repository.insert_expense(conn, data)


def list_expenses(conn: sqlite3.Connection) -> list[Expense]:
    return repository.select_expenses(conn)


def summarize_by_category(conn: sqlite3.Connection) -> list[CategorySummary]:
    return repository.summarize_by_category(conn)


def remove_expense(conn: sqlite3.Connection, expense_id: int) -> None:
    if not repository.delete_expense(conn, expense_id):
        raise ExpenseNotFoundError(expense_id)


def set_monthly_limit(conn: sqlite3.Connection, amount: float) -> None:
    repository.upsert_monthly_limit(conn, amount)


def check_budget(conn: sqlite3.Connection, year: int, month: int) -> BudgetStatus:
    limit = repository.select_monthly_limit(conn)
    if limit is None:
        raise LimitNotSetError()

    spent = sum(
        e.amount
        for e in list_expenses(conn)
        if e.spent_on.year == year and e.spent_on.month == month
    )
    return BudgetStatus(
        year=year,
        month=month,
        limit=limit,
        spent=spent,
        over_limit=spent > limit,
        over_by=max(0.0, spent - limit),
    )

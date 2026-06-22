from datetime import datetime, timezone

from app import config, repository
from app.models import BudgetAlert, Expense, ExpenseCreate


class ExpenseNotFound(Exception):
    pass


def create_expense(data: ExpenseCreate) -> Expense:
    return repository.create(data)


def list_expenses() -> list[Expense]:
    return repository.list_all()


def summary_by_category() -> dict[str, float]:
    totals: dict[str, float] = {}
    for e in list_expenses():
        totals[e.category] = totals.get(e.category, 0.0) + e.amount
    return totals


def delete_expense(expense_id: int) -> None:
    if not repository.delete(expense_id):
        raise ExpenseNotFound(expense_id)


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def budget_alert(month: str | None = None) -> BudgetAlert:
    month = month or _current_month()
    spent = sum(
        e.amount for e in list_expenses() if e.created_at.startswith(month)
    )
    limit = config.MONTHLY_LIMIT
    return BudgetAlert(
        month=month,
        limit=limit,
        spent=spent,
        remaining=limit - spent,
        over_limit=spent > limit,
    )

from app import db
from app.schemas import Expense, ExpenseCreate


def create_expense(data: ExpenseCreate) -> Expense:
    row = db.insert_expense(data.description, data.amount)
    return Expense(**row)


def list_expenses() -> list[Expense]:
    return [Expense(**row) for row in db.fetch_expenses()]


def remove_expense(expense_id: int) -> bool:
    return db.delete_expense(expense_id)

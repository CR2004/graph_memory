from fastapi import APIRouter, HTTPException, status

from app import service
from app.models import BudgetAlert, Expense, ExpenseCreate
from app.service import ExpenseNotFound

router = APIRouter(prefix="/expenses", tags=["expenses"])
budget_router = APIRouter(prefix="/budget", tags=["budget"])


@router.post("", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(data: ExpenseCreate) -> Expense:
    return service.create_expense(data)


@router.get("", response_model=list[Expense])
def list_expenses() -> list[Expense]:
    return service.list_expenses()


@router.get("/summary", response_model=dict[str, float])
def summary() -> dict[str, float]:
    return service.summary_by_category()


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int) -> None:
    try:
        service.delete_expense(expense_id)
    except ExpenseNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )


@budget_router.get("/alert", response_model=BudgetAlert)
def budget_alert(month: str | None = None) -> BudgetAlert:
    return service.budget_alert(month)

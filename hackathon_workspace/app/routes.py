from fastapi import APIRouter, HTTPException, status

from app import service
from app.schemas import Expense, ExpenseCreate

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create(data: ExpenseCreate) -> Expense:
    return service.create_expense(data)


@router.get("", response_model=list[Expense])
def list_all() -> list[Expense]:
    return service.list_expenses()


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(expense_id: int) -> None:
    if not service.remove_expense(expense_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

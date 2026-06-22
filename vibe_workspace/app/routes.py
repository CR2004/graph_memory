import sqlite3
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status

from app import service
from app.database import get_connection
from app.models import (
    BudgetStatus,
    CategorySummary,
    Expense,
    ExpenseCreate,
    MonthlyLimit,
)
from app.service import ExpenseNotFoundError, LimitNotSetError

router = APIRouter(prefix="/expenses", tags=["expenses"])
budget_router = APIRouter(prefix="/budget", tags=["budget"])


def get_db() -> Iterator[sqlite3.Connection]:
    with get_connection() as conn:
        yield conn


@router.post("", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: ExpenseCreate, conn: sqlite3.Connection = Depends(get_db)
) -> Expense:
    return service.create_expense(conn, data)


@router.get("", response_model=list[Expense])
def list_expenses(conn: sqlite3.Connection = Depends(get_db)) -> list[Expense]:
    return service.list_expenses(conn)


@router.get("/summary", response_model=list[CategorySummary])
def summary(conn: sqlite3.Connection = Depends(get_db)) -> list[CategorySummary]:
    return service.summarize_by_category(conn)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int, conn: sqlite3.Connection = Depends(get_db)
) -> None:
    try:
        service.remove_expense(conn, expense_id)
    except ExpenseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@budget_router.put("/monthly-limit", status_code=status.HTTP_204_NO_CONTENT)
def set_monthly_limit(
    data: MonthlyLimit, conn: sqlite3.Connection = Depends(get_db)
) -> None:
    service.set_monthly_limit(conn, data.amount)


@budget_router.get("/alert", response_model=BudgetStatus)
def budget_alert(
    year: int, month: int, conn: sqlite3.Connection = Depends(get_db)
) -> BudgetStatus:
    try:
        return service.check_budget(conn, year, month)
    except LimitNotSetError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

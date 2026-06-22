from datetime import date

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    spent_on: date
    category: str = Field(default="uncategorized", min_length=1, max_length=64)


class Expense(ExpenseCreate):
    id: int


class CategorySummary(BaseModel):
    category: str
    total: float


class MonthlyLimit(BaseModel):
    amount: float = Field(ge=0)


class BudgetStatus(BaseModel):
    year: int
    month: int
    limit: float
    spent: float
    over_limit: bool
    over_by: float

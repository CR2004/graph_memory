from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=64)


class Expense(ExpenseCreate):
    id: int
    created_at: str


class BudgetAlert(BaseModel):
    month: str
    limit: float
    spent: float
    remaining: float
    over_limit: bool

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1)
    amount: float = Field(gt=0)


class Expense(ExpenseCreate):
    id: int

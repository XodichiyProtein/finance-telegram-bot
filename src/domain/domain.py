from dataclasses import dataclass
from datetime import datetime
from typing import Final


@dataclass(frozen=True)
class Category:
    code: str  # например: "needs:food"
    title: str  # "Нужды: еда"


@dataclass
class Expense:
    user_id: int
    amount: float
    description: str
    category_code: str
    created_at: datetime


MONTHLY_LIMITS: Final[dict[str, float]] = {
    "needs:food": 12000.0,
    "needs:transport": 1000.0,
    "wants:electronics": 1000.0,
    "fun:fastfood": 2000.0,
}

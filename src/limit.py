from datetime import datetime
from typing import Final

class LimitsService:
    _LIMITS: Final[dict[str, float]] = MONTHLY_LIMITS

    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    def get_limits_view(self, user_id: int) -> str:
        now = datetime.now()
        summary = self._repository.get_month_summary(user_id, now.month, now.year)

        lines: list[str] = []
        lines.append(f"Лимиты на {now.strftime('%m.%Y')}:")
        total_limit = sum(self._LIMITS.values())
        total_spent = 0.0

        for category_code, limit in self._LIMITS.items():
            spent = summary.get(category_code, 0.0)
            total_spent += spent
            remaining = limit - spent
            percent = (spent / limit * 100) if limit > 0 else 0.0
            lines.append(
                f"- {category_code}: потрачено {spent:.0f} / {limit:.0f} ₽ "
                f"(осталось {remaining:.0f} ₽, {percent:.0f}%)",
            )

        lines.append(
            f"\nИтого: {total_spent:.0f} / {total_limit:.0f} ₽ "
            f"(осталось {total_limit - total_spent:.0f} ₽)",
        )
        return "\n".join(lines)

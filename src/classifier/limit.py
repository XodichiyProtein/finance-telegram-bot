"""
Limits Service
Управление лимитами расходов и отображение статусов
"""

from datetime import datetime
from typing import Final
from src.domain.domain import MONTHLY_LIMITS
from src.storage.storage import ExpenseRepository
from src.core.logger import setup_logger

logger = setup_logger(__name__)


class LimitsService:
    """SRP: сервис лимитов расходов."""

    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository
        self._limits: Final[dict[str, float]] = MONTHLY_LIMITS

    def get_category_limit(self, category_code: str) -> float:
        """Возвращает лимит для категории."""
        return self._limits.get(category_code, 0.0)

    def get_limits_view(self, user_id: int) -> str:
        """Формирует текстовое представление лимитов."""
        now = datetime.now()
        summary = self._repository.get_month_summary(user_id, now.month, now.year)

        lines: list[str] = []
        lines.append(f"💰 *Лимиты на {now.strftime('%B %Y')}*:")
        lines.append("")

        total_limit = sum(self._limits.values())
        total_spent = 0.0

        for category_code, limit in self._limits.items():
            spent = summary.get(category_code, 0.0)
            total_spent += spent
            remaining = limit - spent
            percent = (spent / limit * 100) if limit > 0 else 0.0

            status = self._get_status_emoji(remaining, limit)
            category_name = self._format_category_name(category_code)

            lines.append(
                f"• *{category_name}*\n"
                f"  `{spent:6,.0f}` / `{limit:6,.0f}` ₽  |  "
                f"`{remaining:5,.0f}`  `{percent:3.0f}%` {status}"
            )

        total_remaining = total_limit - total_spent
        total_percent = (total_spent / total_limit * 100) if total_limit > 0 else 0

        lines.append("")
        lines.append(
            f"_Итого:_ *{total_spent:6,.0f}* / *{total_limit:6,.0f}* ₽ "
            f"(*{total_remaining:5,.0f}* осталось, *{total_percent:3.0f}%* использован)"
        )

        return "\n".join(lines)

    def _get_status_emoji(self, remaining: float, limit: float) -> str:
        """Определяет статус категории по остатку."""
        if remaining < 0:
            return "🔴"
        if remaining / limit < 0.2:
            return "🟠"
        if remaining / limit < 0.5:
            return "🟡"
        return "🟢"

    def _format_category_name(self, category_code: str) -> str:
        """Преобразует код категории в читаемое имя."""
        mapping = {
            "needs:food": "🍎 Еда",
            "needs:transport": "🚌 Транспорт",
            "wants:electronics": "📱 Гаджеты",
            "fun:fastfood": "🍔 Фастфуд",
            "needs:clothes": "👕 Одежда",
            "wants:courses": "📚 Курсы",
            "fun:games": "🎮 Игры",
        }
        return mapping.get(category_code, category_code.replace(":", " → "))

"""
Expense Message Handler
Обрабатывает сообщения вида "описание сумма"
"""

import re
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.ext import Application
from src.core.logger import setup_logger
from src.domain.domain import Expense
from src.storage.storage import ExpenseRepository
from src.classifier.classifier import init_classifier
from src.classifier.limit import LimitsService
from src.config.config import Config

logger = setup_logger(__name__)
repo = ExpenseRepository(Config.DB_PATH)
classifier = init_classifier()
limits_service = LimitsService(repo)


async def parse_expense_message(text: str) -> tuple[str, float]:
    """Парсит 'кофе 200' → ('кофе', 200.0)"""
    parts = re.split(r"\s+", text.strip(), maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Формат: `описание сумма`\nПример: `кофе 200`")

    description, amount_str = parts
    amount = float(amount_str.replace(",", "."))
    if amount <= 0:
        raise ValueError("Сумма должна быть > 0")

    return description.strip(), amount


async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главная логика обработки расходов."""
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    text = update.message.text.strip()

    try:
        description, amount = await parse_expense_message(text)
        category_code = classifier.classify(description)

        # Сохраняем расход
        expense = Expense(
            user_id=user_id,
            amount=amount,
            description=description,
            category_code=category_code,
            created_at=datetime.now(),
        )
        repo.add(expense)

        # Показываем статус категории
        summary = repo.get_month_summary(
            user_id, datetime.now().month, datetime.now().year
        )
        spent_in_category = summary.get(category_code, 0.0)

        limit = limits_service.get_category_limit(category_code)
        remaining = limit - spent_in_category if limit else 0

        status_emoji = (
            "🔴" if remaining < 0 else "🟢" if remaining > limit * 0.5 else "🟡"
        )

        response = (
            f"✅ Записано: *{description}* `{amount:,.0f}₽`\n"
            f"📂 Категория: `{category_code}`\n"
            f"💰 По категории: `{spent_in_category:,.0f}/{limit:,.0f}` {status_emoji}\n"
            f"📊 Остаток: `{remaining:,.0f}₽`"
        )

        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info(
            f"Расход добавлен: user={user_id}, {description} {amount}₽ ({category_code})"
        )

    except ValueError as e:
        await update.message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        logger.warning(f"Ошибка парсинга: {text} от {user_id}")
    except Exception as e:
        await update.message.reply_text("❌ Ошибка обработки. Попробуй ещё раз.")
        logger.error(f"Критическая ошибка в handle_expense: {e}", exc_info=True)


def register_expenses(app: Application) -> None:
    """Регистрирует handler для расходов."""
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))

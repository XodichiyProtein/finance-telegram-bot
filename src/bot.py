import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from src.classifier import ExpenseClassifier
from src.limit import LimitsService
from src.storage import ExpenseRepository
from src.domain import MONTHLY_LIMITS

DB_PATH = Path("expenses.db")
TOKEN = "ТОКЕН_ТВОЕГО_БОТА_ОТ_BOTFATHER"

classifier = ExpenseClassifier()
repository = ExpenseRepository(DB_PATH)
limits_service = LimitsService(repository)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Привет! Я бот-учётчик.\n\n"
        "Отправь сообщение в формате:\n"
        "`описание сумма`\n"
        "Примеры: `кофе 200`, `магнит 450`.\n\n"
        "Команды:\n"
        "/limits — показать лимиты на месяц\n"
        "/history — последние траты"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def _parse_expense_message(text: str) -> tuple[str, float]:
    parts = text.strip().rsplit(" ", 1)
    if len(parts) != 2:
        msg = "Нужно: описание и сумма, пример: `кофе 200`"
        raise ValueError(msg)
    description, amount_str = parts
    amount = float(amount_str.replace(",", "."))
    return description, amount


async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None:
        return

    user_id = update.message.from_user.id  # type: ignore[assignment]
    text = update.message.text

    try:
        description, amount = _parse_expense_message(text)
    except ValueError as error:
        await update.message.reply_text(str(error))
        return

    category_code = classifier.classify(description)

    expense = Expense(
        user_id=user_id,
        amount=amount,
        description=description,
        category_code=category_code,
        created_at=datetime.now(),
    )
    repository.add(expense)

    summary = repository.get_month_summary(user_id, datetime.now().month, datetime.now().year)
    spent_in_category = summary.get(category_code, 0.0)
    limit_for_category = MONTHLY_LIMITS.get(category_code)
    remaining_text = ""

    if limit_for_category is not None:
        remaining = limit_for_category - spent_in_category
        remaining_text = f"\nПо категории {category_code} осталось {remaining:.0f} ₽."

    await update.message.reply_text(
        f"Записал: {description} {amount:.0f} ₽ в {category_code}.{remaining_text}",
    )


async def show_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    user_id = update.message.from_user.id  # type: ignore[assignment]
    text = limits_service.get_limits_view(user_id)
    await update.message.reply_text(text)


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    user_id = update.message.from_user.id  # type: ignore[assignment]
    expenses = repository.get_last_expenses(user_id, limit=10)

    if not expenses:
        await update.message.reply_text("Пока нет записей.")
        return

    lines: list[str] = ["Последние траты:"]
    for exp in expenses:
        date_str = exp.created_at.strftime("%d.%m %H:%M")
        lines.append(
            f"- {date_str} — {exp.description} {exp.amount:.0f} ₽ ({exp.category_code})",
        )

    await update.message.reply_text("\n".join(lines))


async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("limits", show_limits))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_expense,
        ),
    )

    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())

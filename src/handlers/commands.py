"""
Command Handlers
/start, /limits, /history
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

from src.core.logger import setup_logger
from src.classifier.limit import LimitsService
from src.storage.storage import ExpenseRepository
from src.config.config import Config

logger = setup_logger(__name__)
repo = ExpenseRepository(Config.DB_PATH)
limits_service = LimitsService(repo)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start."""
    welcome_text = (
        "💰 *Finance Bot*\n\n"
        "📝 Отправь трату в формате:\n"
        "`кофе 200` или `магнит 450`\n\n"
        "📊 Команды:\n"
        "/limits — лимиты на месяц\n"
        "/history — последние траты"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Старт от user={update.message.from_user.id}")


async def show_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /limits."""
    user_id = update.message.from_user.id
    limits_text = limits_service.get_limits_view(user_id)

    await update.message.reply_text(limits_text, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Limits запрошен user={user_id}")


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /history."""
    user_id = update.message.from_user.id
    expenses = repo.get_last_expenses(user_id, limit=10)

    if not expenses:
        await update.message.reply_text("📭 История пуста")
        return

    lines = ["📋 *Последние траты:*"]
    for expense in expenses:
        date_str = expense.created_at.strftime("%d.%m %H:%M")
        lines.append(
            f"• `{date_str}` {expense.description} "
            f"`{expense.amount:,.0f}₽` _{expense.category_code}_"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    logger.info(f"History запрошен user={user_id}")


def register_commands(app: Application) -> None:
    """Регистрация команд."""
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("limits", show_limits))
    app.add_handler(CommandHandler("history", show_history))

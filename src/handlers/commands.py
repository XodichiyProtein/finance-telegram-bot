"""
Обработчики команд Telegram‑бота: /start, /limits и /history.

Модуль инкапсулирует регистрацию и реализацию основных команд бота:
- /start — приветственное сообщение и краткая инструкция по формату ввода;
- /limits — отображение текущих месячных лимитов пользователя;
- /history — последние зафиксированные траты.

Функция register_commands() выступает единой точкой подключения хендлеров
к экземпляру Application из python-telegram-bot. Все обработчики написаны
в асинхронном стиле и используют ContextTypes.DEFAULT_TYPE.
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
    """
    Обработчик команды /start.

    Отправляет приветственное сообщение с кратким описанием функционала бота
    и примерами ввода расходов в текстовом формате. Использует Markdown для
    базового форматирования ответа.

    Parameters
    ----------
    update : Update
        Объект обновления Telegram, содержащий данные о сообщении и пользователе.
    context : ContextTypes.DEFAULT_TYPE
        Контекст выполнения обработчика, предоставляемый python-telegram-bot.
    """
    welcome_text = (
        "💰 *Finance Bot*\n\n"
        "📝 Отправь трату в формате:\n"
        "`кофе 200` или `магнит 450`\n\n"
        "📊 Команды:\n"
        "/limits — лимиты на месяц\n"
        "/history — последние траты"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    logger.info("Старт от user=%s", update.message.from_user.id)


async def show_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /limits.

    Запрашивает у сервиса лимитов агрегированную информацию по месячным
    ограничениям пользователя и отправляет её в виде форматированного
    Markdown‑сообщения.

    Parameters
    ----------
    update : Update
        Объект обновления Telegram.
    context : ContextTypes.DEFAULT_TYPE
        Контекст выполнения обработчика.
    """
    user_id = update.message.from_user.id
    limits_text = limits_service.get_limits_view(user_id)

    await update.message.reply_text(limits_text, parse_mode=ParseMode.MARKDOWN)
    logger.info("Limits запрошен user=%s", user_id)


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /history.

    Получает последние N (по умолчанию 10) расходов пользователя из хранилища
    и рендерит их в читаемый список с датой, описанием, суммой и категорией.
    Если история пуста — отправляет отдельное уведомление.

    Parameters
    ----------
    update : Update
        Объект обновления Telegram.
    context : ContextTypes.DEFAULT_TYPE
        Контекст выполнения обработчика.
    """
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
            f"`{expense.amount:,.0f}₽` _{expense.category_code}_",
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    logger.info("History запрошен user=%s", user_id)


def register_commands(app: Application) -> None:
    """
    Зарегистрировать обработчики команд в приложении Telegram‑бота.

    Функция является единой точкой подключения команд к экземпляру Application,
    чтобы конфигурация хендлеров была централизованной и не разъезжалась
    по коду.

    Parameters
    ----------
    app : Application
        Экземпляр приложения python-telegram-bot, на котором регистрируются
        обработчики команд.
    """
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("limits", show_limits))
    app.add_handler(CommandHandler("history", show_history))

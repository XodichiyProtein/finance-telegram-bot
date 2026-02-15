"""
Обработчик текстовых сообщений с расходами.

Модуль отвечает за приём произвольных текстовых сообщений пользователя вида
«описание сумма», парсинг введённых данных, классификацию трат по категориям,
сохранение в хранилище и отображение текущего статуса по лимитам.

Функция register_expenses() регистрирует единый MessageHandler, который
реагирует на любые текстовые сообщения, не являющиеся командами Telegram.
"""

import re
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, Application
from telegram.constants import ParseMode

from src.core.logger import setup_logger
from src.domain.domain import Expense
from src.storage.storage import ExpenseRepository
from src.classifier.classifier import ExpenseClassifier
from src.classifier.limit import LimitsService
from src.config.config import Config

logger = setup_logger(__name__)
repo = ExpenseRepository(Config.DB_PATH)
classifier = ExpenseClassifier()
limits_service = LimitsService(repo)


async def parse_expense_message(text: str) -> tuple[str, float]:
    """
    Распарсить строку расхода вида «описание сумма».

    Ожидается формат вроде: "кофе 200" или "магнит 450". Левая часть строки
    интерпретируется как произвольное текстовое описание, правая — как сумма
    в виде числа (поддерживается точка и запятая в качестве разделителя).

    Parameters
    ----------
    text : str
        Исходный текст сообщения пользователя.

    Returns
    -------
    tuple[str, float]
        Кортеж (description, amount), где description — очищенное описание,
        а amount — положительное числовое значение суммы.

    Raises
    ------
    ValueError
        Если формат сообщения некорректен или сумма не является положительным
        числом.
    """
    parts = re.split(r"\s+", text.strip(), maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Формат: `описание сумма`\nПример: `кофе 200`")

    description, amount_str = parts
    amount = float(amount_str.replace(",", "."))
    if amount <= 0:
        raise ValueError("Сумма должна быть > 0")

    return description.strip(), amount


async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Главный обработчик текстовых сообщений с расходами.

    Логика:
    1. Парсит сообщение в (описание, сумма).
    2. Классифицирует расход по категории.
    3. Сохраняет запись в репозитории.
    4. Считает суммарные траты по категории за текущий месяц и сравнивает
       их с лимитом.
    5. Отправляет пользователю ответ с краткой сводкой и статус‑эмодзи.

    Parameters
    ----------
    update : Update
        Объект обновления Telegram, содержащий сообщение пользователя.
    context : ContextTypes.DEFAULT_TYPE
        Контекст выполнения обработчика.

    Notes
    -----
    В случае ошибки парсинга пользователь получает подсказку по формату.
    При неожиданных исключениях отправляется краткое сообщение об ошибке,
    а детали пишутся в лог.
    """
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    text = update.message.text.strip()

    try:
        description, amount = await parse_expense_message(text)
        category_code = classifier.classify(description)

        expense = Expense(
            user_id=user_id,
            amount=amount,
            description=description,
            category_code=category_code,
            created_at=datetime.now(),
        )
        repo.add(expense)

        summary = repo.get_month_summary(
            user_id,
            datetime.now().month,
            datetime.now().year,
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
            "Расход добавлен: user=%s, %s %s₽ (%s)",
            user_id,
            description,
            amount,
            category_code,
        )

    except ValueError as e:
        await update.message.reply_text(str(e), parse_mode=ParseMode.MARKDOWN)
        logger.warning("Ошибка парсинга: %s от %s", text, user_id)
    except Exception as e:  # noqa: BLE001 — здесь логируем критические ошибки
        await update.message.reply_text("❌ Ошибка обработки. Попробуй ещё раз.")
        logger.error("Критическая ошибка в handle_expense: %s", e, exc_info=True)


def register_expenses(app: Application) -> None:
    """
    Зарегистрировать обработчик текстовых расходов в приложении бота.

    Подключает MessageHandler, который реагирует на любые текстовые сообщения
    (filters.TEXT) за исключением команд (filters.COMMAND), и направляет их
    в handle_expense().

    Parameters
    ----------
    app : Application
        Экземпляр приложения python-telegram-bot, на котором регистрируется
        обработчик.
    """
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))

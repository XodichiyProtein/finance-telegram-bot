"""
Bot Application Factory
Единая точка создания настроенного приложения
"""

from telegram.ext import Application
from src.config.config import Config
from src.core.logger import setup_logger
from src.handlers import register_handlers

logger = setup_logger(__name__)


def create_application() -> Application:
    """
    Создаёт полностью настроенное приложение.

    Возвращает Application с зарегистрированными handlers.
    """
    if not Config.TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не настроен")

    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()

    register_handlers(app)

    logger.info("✅ Bot Application создано")
    return app

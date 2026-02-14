"""
Finance Telegram Bot Entry Point
Единая точка входа (main)
"""

import sys
from src.core.logger import setup_logger
from src.core.validators import validate_environment
from src.bot import create_application


def main() -> None:
    """Главная точка входа."""
    logger = setup_logger()

    try:
        logger.info("🚀 Запускаем Finance Telegram Bot...")
        validate_environment()

        app = create_application()
        app.run_polling(drop_pending_updates=True)

    except KeyboardInterrupt:
        logger.info("🛑 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

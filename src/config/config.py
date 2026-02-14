"""
Конфигурация приложения и переменные окружения
"""

from pathlib import Path
from typing import Final
from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    TELEGRAM_TOKEN: Final[str] = os.getenv("TELEGRAM_TOKEN", "")
    DB_PATH: Final[Path] = Path(os.getenv("DB_PATH", "expenses.db"))

    @classmethod
    def validate(cls) -> None:
        """SRP: проверка обязательных переменных."""
        if not cls.TELEGRAM_TOKEN:
            raise ValueError("❌ TELEGRAM_TOKEN не найден в .env!")

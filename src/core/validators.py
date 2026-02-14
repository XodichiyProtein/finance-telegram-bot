"""
Валидаторы конфигурации
"""

from src.config.config import Config


def validate_environment() -> None:
    """Валидация окружения."""
    Config.validate()

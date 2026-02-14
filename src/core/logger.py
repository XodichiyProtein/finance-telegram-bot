"""
Настройка логирования (единая точка)
"""

import logging  # стандартный модуль
import sys
from typing import Final
from logging import Logger, StreamHandler

LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(message)s"


def setup_logger(name: str = __name__, level: str = "INFO") -> Logger:
    """SRP: настройка логгера."""
    # Правильные уровни логирования
    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        handlers=[StreamHandler(sys.stdout)],
        force=True,  # ← перезаписывает предыдущую настройку
    )

    return logging.getLogger(name)

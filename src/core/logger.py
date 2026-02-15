"""
Настройка логирования приложения (единая точка входа).

Модуль инкапсулирует конфигурацию стандартного logging, чтобы в остальном
коде не дублировать настройку форматирования, уровней и хендлеров.

Основная функция — setup_logger(), которая:
- конфигурирует базовую систему логирования;
- выбирает уровень логов на основе строкового параметра;
- возвращает именованный логгер, готовый к использованию в любом модуле.
"""

import logging
import sys
from typing import Final
from logging import Logger, StreamHandler


LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(message)s"


def setup_logger(name: str = __name__, level: str = "INFO") -> Logger:
    """
    Создать и настроить логгер приложения.

    Функция задаёт формат сообщений, подключает вывод в stdout и устанавливает
    глобальный уровень логирования через logging.basicConfig(). Уровень
    передаётся строкой (например, "DEBUG" или "ERROR") и маппится на
    соответствующее значение из logging.

    Parameters
    ----------
    name : str, optional
        Имя логгера, обычно __name__ модуля, который вызывает функцию.
    level : str, optional
        Строковый уровень логирования: "DEBUG", "INFO", "WARNING",
        "ERROR" или "CRITICAL". Значения в нижнем регистре также
        поддерживаются. При некорректном значении используется "INFO".

    Returns
    -------
    Logger
        Сконфигурированный экземпляр логгера, готовый к использованию во всём
        приложении.
    """
    log_levels: dict[str, int] = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = log_levels.get(level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        handlers=[StreamHandler(sys.stdout)],
        force=True,  # Явно перезаписывает предыдущую конфигурацию logging
    )

    return logging.getLogger(name)

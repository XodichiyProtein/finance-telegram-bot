"""
Handlers Registry
Единая точка регистрации всех handlers
"""

from telegram.ext import Application

from src.handlers.commands import register_commands
from src.handlers.expenses import register_expenses


def register_handlers(app: Application) -> None:
    """Регистрация всех handlers."""
    register_commands(app)
    register_expenses(app)

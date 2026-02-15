"""
Хранилище расходов на SQLite.

Модуль инкапсулирует всю работу с базой данных расходов:
- инициализацию схемы (создание таблицы expenses при первом запуске);
- добавление новых записей о тратах;
- получение агрегированных сумм по категориям за выбранный месяц;
- выборку последних N расходов пользователя.

Основной класс — ExpenseRepository. Он принимает путь к файлу БД и
предоставляет простой API для остального приложения, не раскрывая деталей
SQL и подключения.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

from src.domain.domain import Expense


class ExpenseRepository:
    """
    Репозиторий для работы с таблицей расходов в SQLite.

    Отвечает за создание таблицы, выполнение CRUD‑операций и возврат
    доменных объектов Expense вместо «сырых» строк из базы.

    Parameters
    ----------
    db_path : Path
        Путь к файлу базы данных SQLite. Если файла ещё нет, он будет создан.

    Attributes
    ----------
    _db_path : Path
        Внутренний путь к файлу базы данных, используемый для подключений.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self):
        """
        Создать контекстное подключение к базе данных.

        Используется как внутренний helper: открывает соединение при входе
        в контекст и гарантированно закрывает его при выходе, независимо
        от того, возникло ли исключение.

        Yields
        ------
        sqlite3.Connection
            Активное соединение с базой данных.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """
        Инициализировать схему базы данных, если она ещё не создана.

        Создаёт таблицу expenses с полями:
        - id: первичный ключ;
        - user_id: идентификатор пользователя;
        - amount: сумма расхода;
        - description: текстовое описание;
        - category_code: код категории;
        - created_at: дата и время в ISO‑формате.
        """
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    category_code TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """,
            )
            conn.commit()

    def add(self, expense: Expense) -> None:
        """
        Добавить новый расход в базу данных.

        Parameters
        ----------
        expense : Expense
            Доменный объект расхода, который необходимо сохранить.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, description, category_code, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    expense.user_id,
                    expense.amount,
                    expense.description,
                    expense.category_code,
                    expense.created_at.isoformat(),
                ),
            )
            conn.commit()

    def get_month_summary(
        self, user_id: int, month: int, year: int
    ) -> dict[str, float]:
        """
        Получить агрегированные суммы расходов по категориям за месяц.

        Parameters
        ----------
        user_id : int
            Идентификатор пользователя, для которого считается сводка.
        month : int
            Номер месяца (1–12).
        year : int
            Год (полное четырёхзначное значение).

        Returns
        -------
        dict[str, float]
            Словарь вида {category_code: total_amount}, где total_amount —
            сумма расходов по категории за указанный месяц.
        """
        query = """
            SELECT category_code, SUM(amount)
            FROM expenses
            WHERE user_id = ?
              AND strftime('%m', created_at) = ?
              AND strftime('%Y', created_at) = ?
            GROUP BY category_code
        """
        with self._connect() as conn:
            cursor = conn.execute(query, (user_id, f"{month:02d}", str(year)))
            rows = cursor.fetchall()

        summary: dict[str, float] = {}
        for category_code, total_amount in rows:
            summary[category_code] = float(total_amount)
        return summary

    def get_last_expenses(self, user_id: int, limit: int = 10) -> list[Expense]:
        """
        Получить список последних расходов пользователя.

        Parameters
        ----------
        user_id : int
            Идентификатор пользователя.
        limit : int, optional
            Максимальное количество записей, которое нужно вернуть.
            По умолчанию — 10.

        Returns
        -------
        list[Expense]
            Список доменных объектов Expense, отсортированных по дате
            создания в порядке убывания (от новых к старым).
        """
        query = """
            SELECT user_id, amount, description, category_code, created_at
            FROM expenses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            cursor = conn.execute(query, (user_id, limit))
            rows = cursor.fetchall()

        expenses: list[Expense] = []
        for row in rows:
            expenses.append(
                Expense(
                    user_id=row[0],
                    amount=row[1],
                    description=row[2],
                    category_code=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                ),
            )
        return expenses

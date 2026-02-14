import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from src.domain.domain import Expense


class ExpenseRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
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

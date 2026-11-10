"""Третий этап: SQLite и параметризованные SQL-запросы."""

import sqlite3
from pathlib import Path

from src.report import recent_interval
from src.schema import Record
from src.storage import Storage


schema_sql = """
CREATE TABLE IF NOT EXISTS participant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created INTEGER NOT NULL, ip TEXT NOT NULL,
    locale TEXT NOT NULL, user_agent TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS command (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created INTEGER NOT NULL, parameter TEXT NOT NULL,
    participant INTEGER NOT NULL REFERENCES participant(id),
    description TEXT NOT NULL, tags TEXT NOT NULL, spawned INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reply (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created INTEGER NOT NULL, response TEXT NOT NULL,
    status TEXT NOT NULL, exception TEXT NOT NULL,
    command INTEGER NOT NULL REFERENCES command(id),
    cache_hit INTEGER NOT NULL, duration INTEGER NOT NULL
);
"""
report_sql = """
SELECT DISTINCT c.description, p.ip, r.response
FROM command AS c
LEFT JOIN participant AS p ON p.id = c.participant
LEFT JOIN reply AS r ON c.id = r.command
WHERE c.created > ?
ORDER BY c.id, r.id
"""


class SqliteStorage(Storage):
    """Использует SQL для создания, поиска, чтения и отчёта."""

    def __init__(self, path: Path) -> None:
        """Открыть SQLite с внешними ключами и создать таблицы."""
        super().__init__()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(schema_sql)

    def _insert(self, entity: str, record: Record) -> Record:
        """Вставить строку, подставив значения через параметры SQL."""
        columns = ", ".join(record)
        placeholders = ", ".join("?" for _ in record)
        sql = "INSERT INTO {} ({}) VALUES ({})".format(
            entity, columns, placeholders,
        )
        with self.connection:
            cursor = self.connection.execute(sql, tuple(record.values()))
        return dict(record, id=cursor.lastrowid)

    def _select(self, entity: str, filters: Record) -> list[Record]:
        """Выполнить SELECT с проверенными именами и параметрами."""
        sql = "SELECT * FROM " + entity
        if filters:
            sql += " WHERE " + " AND ".join(key + " = ?" for key in filters)
        sql += " ORDER BY id"
        return [
            dict(row) for row in self.connection.execute(
                sql, tuple(filters.values()),
            )
        ]

    def _mark_spawned(self, command_id: int) -> None:
        """Обновить признак запуска параметризованным UPDATE."""
        with self.connection:
            self.connection.execute(
                "UPDATE command SET spawned = ? WHERE id = ?",
                (1, command_id),
            )

    def report(self) -> list[Record]:
        """Выполнить внешние соединения, фильтр времени и DISTINCT в SQL."""
        with self.lock:
            threshold = int(self.clock()) - recent_interval
            return [
                dict(row) for row in self.connection.execute(
                    report_sql, (threshold,),
                )
            ]

    def close(self) -> None:
        """Закрыть соединение SQLite."""
        self.connection.close()

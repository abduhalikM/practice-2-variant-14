"""Общий интерфейс и внешние ключи двух дисковых хранилищ."""

import threading
import time
from abc import ABC, abstractmethod

from src.report import build_report
from src.schema import Record, clean_fields, minimum_id, prepare_record


class Storage(ABC):
    """Обеспечивает одинаковые правила для TinyDB и SQLite."""

    def __init__(self) -> None:
        """Создать блокировку и источник времени."""
        self.lock = threading.RLock()
        self.clock = time.time

    def insert(self, entity: str, data: Record) -> Record:
        """Создать запись после проверки структуры и внешней связи."""
        with self.lock:
            record = prepare_record(entity, data, int(self.clock()))
            if entity == "command":
                self.inspect("participant", record["participant"])
            if entity == "reply":
                self.inspect("command", record["command"])
            return self._insert(entity, record)

    def query(self, entity: str, filters: Record | None = None) -> list[Record]:
        """Найти записи по точным совпадениям полей."""
        with self.lock:
            return self._select(entity, clean_fields(entity, filters or {}))

    def inspect(self, entity: str, record_id: int) -> Record:
        """Получить запись по положительному идентификатору."""
        filters = clean_fields(entity, {"id": record_id})
        if filters["id"] < minimum_id:
            raise ValueError("Идентификатор должен быть положительным")
        rows = self.query(entity, filters)
        if not rows:
            raise ValueError("Запись не найдена: " + entity)
        return rows[0]

    def mark_spawned(self, command_id: int) -> None:
        """Пометить команду как переданную на выполнение."""
        with self.lock:
            self.inspect("command", command_id)
            self._mark_spawned(command_id)

    def report(self) -> list[Record]:
        """Вычислить формулу (14) средствами файловой модели."""
        with self.lock:
            return build_report(
                self.query("participant"), self.query("command"),
                self.query("reply"), int(self.clock()),
            )

    @abstractmethod
    def _insert(self, entity: str, record: Record) -> Record:
        """Сохранить проверенную запись и назначить идентификатор."""

    @abstractmethod
    def _select(self, entity: str, filters: Record) -> list[Record]:
        """Выполнить выборку конкретного хранилища."""

    @abstractmethod
    def _mark_spawned(self, command_id: int) -> None:
        """Изменить признак запуска команды в конкретном хранилище."""

    @abstractmethod
    def close(self) -> None:
        """Закрыть дисковое хранилище."""

"""Файловая СУБД TinyDB для второго этапа."""

from pathlib import Path

from tinydb import TinyDB, where
from tinydb.table import Document

from src.schema import Record
from src.storage import Storage


class FileStorage(Storage):
    """Хранит три отношения в JSON-файле через TinyDB."""

    def __init__(self, path: Path) -> None:
        """Открыть или создать файл базы данных."""
        super().__init__()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database = TinyDB(path, encoding="utf-8", ensure_ascii=False)

    def _insert(self, entity: str, record: Record) -> Record:
        """Назначить id и записать документ TinyDB."""
        table = self.database.table(entity, cache_size=0)
        record_id = max((row["id"] for row in table.all()), default=0) + 1
        row = dict(record, id=record_id)
        table.insert(Document(row, doc_id=record_id))
        return row

    def _select(self, entity: str, filters: Record) -> list[Record]:
        """Получить документы, совпадающие со всеми фильтрами."""
        rows = self.database.table(entity, cache_size=0).all()
        return [
            dict(row) for row in rows
            if all(row[key] == value for key, value in filters.items())
        ]

    def _mark_spawned(self, command_id: int) -> None:
        """Обновить spawned у выбранной команды."""
        self.database.table("command").update(
            {"spawned": 1}, where("id") == command_id,
        )

    def close(self) -> None:
        """Закрыть файловую базу данных."""
        self.database.close()

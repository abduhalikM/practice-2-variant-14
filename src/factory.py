"""Выбор слоя доступа к данным без изменения HTTP API."""

from pathlib import Path

from src.file_store import FileStorage
from src.sqlite_store import SqliteStorage
from src.storage import Storage


def open_storage(backend: str, directory: Path) -> Storage:
    """Открыть TinyDB второго этапа или SQLite третьего этапа."""
    if backend == "tinydb":
        return FileStorage(directory / "jobs.json")
    if backend == "sqlite":
        return SqliteStorage(directory / "jobs.sqlite3")
    raise ValueError("Неизвестное хранилище: " + backend)

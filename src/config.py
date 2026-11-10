"""Чтение настроек HTTP API из конфигурационного файла."""

import argparse
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


minimum_port = 0
maximum_port = 65535
minimum_timeout = 0


@dataclass(frozen=True)
class Settings:
    """Адрес, авторизация, хранилище и режим выполнения задач."""

    host: str = "127.0.0.1"
    port: int = 8080
    username: str = "student"
    password: str = "qr-demo"
    backend: str = "sqlite"
    directory: Path = Path("data")
    test_mode: bool = False
    timeout: float = 15.0

    def __post_init__(self) -> None:
        """Отклонить непригодные настройки до открытия базы и сокета."""
        if not minimum_port <= self.port <= maximum_port:
            raise ValueError("Порт вне допустимого диапазона")
        if not self.username or ":" in self.username or not self.password:
            raise ValueError("Нужны логин без двоеточия и непустой пароль")
        if self.backend not in ("tinydb", "sqlite"):
            raise ValueError("Неизвестное хранилище")
        if self.timeout <= minimum_timeout:
            raise ValueError("Тайм-аут должен быть положительным")


def load_settings(path: str = "config.ini") -> Settings:
    """Загрузить конфигурацию относительно расположения INI-файла."""
    parser = ConfigParser(interpolation=None)
    if not parser.read(path, encoding="utf-8"):
        raise ValueError("Не найден файл конфигурации: " + path)
    directory = Path(path).resolve().parent / parser["storage"]["directory"]
    return Settings(
        host=parser["server"]["host"],
        port=parser.getint("server", "port"),
        username=parser["server"]["username"],
        password=parser["server"]["password"],
        backend=parser["storage"]["backend"], directory=directory,
        test_mode=parser.getboolean("tasks", "test_mode"),
        timeout=parser.getfloat("tasks", "timeout"),
    )


def parse_options(description: str) -> argparse.Namespace:
    """Прочитать путь конфигурации и параметры запуска сервера."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default="config.ini")
    parser.add_argument("--backend", choices=("tinydb", "sqlite"))
    parser.add_argument("--test-mode", action="store_true")
    return parser.parse_args()

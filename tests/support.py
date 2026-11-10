"""Изолированный HTTP-сервер и управляемые часы для тестов."""

import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from wsgiref.simple_server import make_server

from src.client import ApiClient
from src.config import Settings
from src.server import QuietHandler, ThreadedServer, create_application


class Clock:
    """Источник времени, который тест изменяет без ожидания минут."""

    def __init__(self) -> None:
        """Установить воспроизводимое начальное Unix-время."""
        self.value = 2000000000

    def __call__(self) -> int:
        """Вернуть текущее тестовое время."""
        return self.value


class LiveApi:
    """Запускает настоящий HTTP API на свободном локальном порту."""

    def __init__(self, backend: str, test_mode: bool = True) -> None:
        """Создать временную СУБД, приложение, сервер и HTTP-клиент."""
        self.directory = TemporaryDirectory()
        self.settings = Settings(
            backend=backend, directory=Path(self.directory.name),
            test_mode=test_mode,
        )
        self.application = create_application(self.settings)
        self.clock = Clock()
        self.application.storage.clock = self.clock
        self.server = make_server(
            "127.0.0.1", 0, self.application.app,
            server_class=ThreadedServer, handler_class=QuietHandler,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01}, daemon=True,
        )
        self.thread.start()
        self.client = ApiClient(
            "http://{}:{}".format(*self.server.server_address),
            self.settings.username, self.settings.password,
        )

    def close(self) -> None:
        """Закрыть сервер, задачи, базу и временную директорию."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.application.close()
        self.directory.cleanup()

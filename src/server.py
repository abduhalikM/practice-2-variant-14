"""Запуск Bottle API с файловой СУБД либо SQLite."""

from dataclasses import dataclass, replace
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from bottle import Bottle

from src.api import ApiHandlers
from src.config import Settings, load_settings, parse_options
from src.factory import open_storage
from src.security import http_error, protect
from src.storage import Storage
from src.tasks import TaskRunner


class ThreadedServer(ThreadingMixIn, WSGIServer):
    """Обслуживает HTTP-запросы независимо от фоновой генерации."""

    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    """Не выводит служебные строки для каждого HTTP-запроса."""

    def log_message(self, format: str, *args: object) -> None:
        """Подавить стандартный журнал WSGI-сервера."""


@dataclass
class Application:
    """Приложение и ресурсы, которые нужно закрыть после работы."""

    app: Bottle
    storage: Storage
    tasks: TaskRunner

    def close(self) -> None:
        """Закончить вычисления и закрыть базу данных."""
        self.tasks.close()
        self.storage.close()


def create_application(settings: Settings) -> Application:
    """Создать девять XML-маршрутов с Basic-авторизацией."""
    storage = open_storage(settings.backend, settings.directory)
    tasks = TaskRunner(storage, settings)
    handlers = ApiHandlers(storage, tasks)
    app = Bottle()
    for method, path, callback in handlers.routes():
        app.route(path, method=method, callback=protect(callback, settings))
    for status in (404, 405, 500):
        app.error(status)(http_error)
    tasks.resume_pending()
    return Application(app, storage, tasks)


def main() -> None:
    """Запустить HTTP API и корректно завершить работу по Ctrl+C."""
    arguments = parse_options("Генерация QR-кодов: HTTP API, вариант 14")
    settings = load_settings(arguments.config)
    settings = replace(
        settings, backend=arguments.backend or settings.backend,
        test_mode=arguments.test_mode or settings.test_mode,
    )
    application = create_application(settings)
    try:
        with make_server(
            settings.host, settings.port, application.app,
            server_class=ThreadedServer, handler_class=QuietHandler,
        ) as server:
            print("HTTP API: http://{}:{}".format(*server.server_address))
            print("Хранилище: {}. Выход: Ctrl+C.".format(settings.backend))
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        application.close()


if __name__ == "__main__":
    main()

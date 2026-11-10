"""HTTP-клиент: XML, Basic-авторизация и девять методов таблицы 14."""

import base64
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import Settings
from src.schema import Record
from src.xml_codec import decode_response, encode_request


poll_interval = 0.02


class ApiError(RuntimeError):
    """Ошибка HTTP либо ошибка операции внутри XML-ответа."""

    def __init__(self, status: int, message: str) -> None:
        """Сохранить код HTTP и текст ошибки."""
        self.status = status
        super().__init__(message)


class ApiClient:
    """Предоставляет методы вида таблица_действие поверх HTTP."""

    def __init__(
        self, base_url: str, username: str, password: str,
        timeout: float = 10.0,
    ) -> None:
        """Сохранить адрес, тайм-аут и заголовок Basic."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        credentials = (username + ":" + password).encode("utf-8")
        self.authorization = "Basic " + base64.b64encode(credentials).decode()

    def request(
        self, method: str, path: str, body: bytes | None = None,
        query: Record | None = None, authorization: str | None = None,
    ) -> object:
        """Отправить HTTP-запрос и разобрать XML, включая ошибки HTTP."""
        suffix = "?" + urlencode(query) if query else ""
        headers = {
            "Authorization": self.authorization if authorization is None
            else authorization,
            "Content-Type": "application/xml; charset=utf-8",
        }
        request = Request(
            self.base_url + path + suffix, data=body,
            headers=headers, method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status, payload = response.status, response.read()
        except HTTPError as error:
            with error:
                status, payload = error.code, error.read()
        data = decode_response(payload)
        if not data.get("ok"):
            raise ApiError(status, data.get("error", "Ошибка API"))
        return data["result"]

    def participant_insert(self, data: Record) -> Record:
        """Создать участника: POST с XML-телом."""
        return self.request(
            "POST", "/api/insert-participant", encode_request(data),
        )

    def participant_query(self, filters: Record | None = None) -> list[Record]:
        """Найти участников по значениям полей в строке запроса."""
        return self.request("POST", "/api/query-participant", query=filters)

    def participant_inspect(self, record_id: int) -> Record:
        """Прочитать участника по id."""
        return self.request(
            "GET", "/api/inspect-participant", query={"id": record_id},
        )

    def command_insert(self, data: Record) -> Record:
        """Создать вычислительную задачу, не ожидая готового SVG."""
        return self.request("POST", "/api/insert-command", encode_request(data))

    def command_query(
        self, participant: int, filters: Record | None = None,
    ) -> list[Record]:
        """Найти команды конкретного участника."""
        return self.request(
            "POST", "/api/query-command/{}".format(participant), query=filters,
        )

    def command_inspect(self, record_id: int) -> Record:
        """Прочитать команду по id."""
        return self.request(
            "GET", "/api/inspect-command", query={"id": record_id},
        )

    def reply_query(
        self, command: int, filters: Record | None = None,
    ) -> list[Record]:
        """Найти ответы конкретной команды."""
        return self.request(
            "POST", "/api/query-reply/{}".format(command), query=filters,
        )

    def reply_inspect(self, record_id: int) -> Record:
        """Прочитать ответ с SVG и статусом выполнения."""
        return self.request(
            "GET", "/api/inspect-reply", query={"id": record_id},
        )

    def report_query(self) -> list[Record]:
        """Получить отчёт по формуле (14)."""
        return self.request("POST", "/api/query-report")

    def wait_for_reply(self, command: int, timeout: float = 20.0) -> Record:
        """Опросить API до появления ответа либо истечения тайм-аута."""
        deadline = time.monotonic() + timeout
        while True:
            replies = self.reply_query(command)
            if replies:
                return replies[-1]
            if time.monotonic() >= deadline:
                raise TimeoutError("Ответ пока не готов")
            time.sleep(poll_interval)


def configured_client(settings: Settings) -> ApiClient:
    """Создать клиент по тому же INI-файлу, что использует сервер."""
    address = "http://{}:{}".format(settings.host, settings.port)
    return ApiClient(address, settings.username, settings.password)

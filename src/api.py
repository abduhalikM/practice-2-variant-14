"""Девять обработчиков таблицы 14: Participant, Command, Reply, Report."""

from bottle import request

from src.schema import Record
from src.storage import Storage
from src.tasks import TaskRunner
from src.xml_codec import decode_request, max_request_bytes


class ApiHandlers:
    """Реализует методы HTTP API независимо от выбранной СУБД."""

    def __init__(self, storage: Storage, tasks: TaskRunner) -> None:
        """Сохранить слой данных и очередь вычислительных задач."""
        self.storage = storage
        self.tasks = tasks

    def _body(self) -> Record:
        """Прочитать ограниченное по размеру XML-тело запроса."""
        with request.body as stream:
            body = stream.read(max_request_bytes + 1)
        if len(body) > max_request_bytes:
            raise ValueError("Тело запроса превышает 1 МиБ")
        return decode_request(body)

    def _record_id(self) -> str:
        """Проверить единственный обязательный параметр id."""
        if set(request.query) != {"id"}:
            raise ValueError("Требуется только параметр id")
        return request.query["id"]

    def _scoped_query(self, entity: str, key: str, value: int) -> list[Record]:
        """Найти записи только в пределах родителя, указанного в пути."""
        filters = dict(request.query)
        if key in filters:
            raise ValueError("Родитель задаётся в пути, а не в строке запроса")
        filters[key] = value
        return self.storage.query(entity, filters)

    def participant_insert(self) -> Record:
        """POST /api/insert-participant: создать участника из XML."""
        return self.storage.insert("participant", self._body())

    def participant_query(self) -> list[Record]:
        """POST /api/query-participant: поиск по параметрам URL."""
        return self.storage.query("participant", dict(request.query))

    def participant_inspect(self) -> Record:
        """GET /api/inspect-participant?id=...: прочитать участника."""
        return self.storage.inspect("participant", self._record_id())

    def command_insert(self) -> Record:
        """POST /api/insert-command: принять задачу и вернуть команду."""
        command = self.storage.insert("command", self._body())
        self.tasks.submit(command)
        return command

    def command_query(self, participant: int) -> list[Record]:
        """POST /api/query-command/:participant: найти команды участника."""
        return self._scoped_query("command", "participant", participant)

    def command_inspect(self) -> Record:
        """GET /api/inspect-command?id=...: прочитать команду."""
        return self.storage.inspect("command", self._record_id())

    def reply_query(self, command: int) -> list[Record]:
        """POST /api/query-reply/:command: найти ответы команды."""
        return self._scoped_query("reply", "command", command)

    def reply_inspect(self) -> Record:
        """GET /api/inspect-reply?id=...: прочитать ответ."""
        return self.storage.inspect("reply", self._record_id())

    def report_query(self) -> list[Record]:
        """POST /api/query-report: получить отчёт по формуле (14)."""
        return self.storage.report()

    def routes(self) -> tuple:
        """Вернуть методы и маршруты строго по таблице 14."""
        return (
            ("POST", "/api/insert-participant", self.participant_insert),
            ("POST", "/api/query-participant", self.participant_query),
            ("GET", "/api/inspect-participant", self.participant_inspect),
            ("POST", "/api/insert-command", self.command_insert),
            ("POST", "/api/query-command/<participant:int>",
             self.command_query),
            ("GET", "/api/inspect-command", self.command_inspect),
            ("POST", "/api/query-reply/<command:int>", self.reply_query),
            ("GET", "/api/inspect-reply", self.reply_inspect),
            ("POST", "/api/query-report", self.report_query),
        )

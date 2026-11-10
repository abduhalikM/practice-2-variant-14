"""Сгенерированные Hypothesis сценарии для всех девяти HTTP-обработчиков."""

import os
import threading
from unittest.mock import patch

from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from src.client import ApiError
from src.xml_codec import max_request_bytes
from tests.reference import ReferenceModel, expected_svg
from tests.support import LiveApi


text_values = st.text(alphabet="abcXYZ0123<&>Я界", min_size=1, max_size=20)
backend = os.environ.get("QR_TEST_BACKEND", "sqlite")
absent_id = 999999
minimum_duration = 0
expected_ok = 200
expected_unauthorized = 401


@settings(
    max_examples=12, stateful_step_count=25,
    deadline=None, derandomize=True, database=None,
)
class ApiMachine(RuleBasedStateMachine):
    """Сравнивает реальный HTTP API с независимой моделью после действий."""

    def __init__(self) -> None:
        """Создать отдельный сервер и эталонное состояние."""
        super().__init__()
        self.live = LiveApi(backend)
        self.client = self.live.client
        self.model = ReferenceModel(self.live.clock.value)

    @initialize(text=text_values)
    def bootstrap(self, text: str) -> None:
        """Сгенерировать исходное состояние и вызвать все обработчики."""
        self._add_participant(text)
        self._add_command(text, 1, 0)
        self._add_pending_command(text)
        self._check_reads()
        self._check_errors()
        self._check_authorization()

    def _assert_record(self, actual: dict, expected: dict) -> None:
        """Сравнить все поля, отдельно проверив измеряемую длительность."""
        actual, expected = dict(actual), dict(expected)
        if "duration" in expected:
            duration = actual.pop("duration")
            expected.pop("duration")
            assert type(duration) is int and duration >= minimum_duration
        assert actual == expected

    def _add_participant(self, name: str) -> None:
        """Создать участника через API и предсказать его запись."""
        data = {"ip": "127.0.0.1", "locale": "ru-RU", "user_agent": name}
        actual = self.client.participant_insert(data)
        expected = self.model.insert("participant", data)
        self._assert_record(actual, expected)

    def _add_command(self, text: str, participant: int, age: int) -> None:
        """Создать задачу и сравнить принятие и асинхронное завершение."""
        data = {
            "participant": participant, "parameter": text,
            "description": "QR " + text, "tags": "mbt",
            "created": self.model.now - age,
        }
        actual = self.client.command_insert(data)
        expected = self.model.insert("command", data)
        self._assert_record(actual, expected)
        reply = self.client.wait_for_reply(actual["id"])
        self._assert_record(reply, self.model.finish(expected["id"]))

    def _check_reads(self) -> None:
        """Сравнить поиск, чтение по id и формулу через HTTP-клиент."""
        expected_participants = self.model.tables["participant"]
        assert self.client.participant_query() == expected_participants
        self._check_inspections()
        self._check_commands()
        self._check_replies()
        self._check_report()

    def _check_inspections(self) -> None:
        """Сравнить чтение каждой записи по идентификатору."""
        for entity in ("participant", "command", "reply"):
            for expected in self.model.tables[entity]:
                inspect = getattr(self.client, entity + "_inspect")
                self._assert_record(inspect(expected["id"]), expected)

    def _check_commands(self) -> None:
        """Сравнить команды каждого участника с эталонной моделью."""
        for participant in self.model.tables["participant"]:
            expected = self.model.query(
                "command", {"participant": participant["id"]},
            )
            assert self.client.command_query(participant["id"]) == expected

    def _check_replies(self) -> None:
        """Сравнить количество и содержимое ответов каждой команды."""
        for command in self.model.tables["command"]:
            actual = self.client.reply_query(command["id"])
            expected = self.model.query("reply", {"command": command["id"]})
            assert len(actual) == len(expected)
            for row, reference in zip(actual, expected):
                self._assert_record(row, reference)

    def _check_report(self) -> None:
        """Сравнить проекцию отчёта и проверить отсутствие повторов."""
        rows = self.client.report_query()
        projection = {
            (row["description"], row["ip"], row["response"]) for row in rows
        }
        assert projection == self.model.report()
        assert len(rows) == len(projection)

    def _assert_error(self, method: str, path: str, **kwargs: object) -> None:
        """Проверить, что ошибочный запрос возвращает XML-ошибку с HTTP 200."""
        try:
            self.client.request(method, path, **kwargs)
        except ApiError as error:
            assert error.status == expected_ok
        else:
            raise AssertionError("Ожидалась ошибка API")

    def _check_errors(self) -> None:
        """Проверить границы тела, XML, идентификаторы и область поиска."""
        insert = "/api/insert-participant"
        for body in (b"<wrong/>", b"<request><ip><x/></ip></request>",
                     b"<request><ip/><ip/></request>", b"<request>",
                     b"<request/>", b"x" * (max_request_bytes + 1)):
            self._assert_error("POST", insert, body=body)
        for entity in ("participant", "command", "reply"):
            path = "/api/inspect-" + entity
            for query in ({}, {"id": "bad"}, {"id": -1}, {"id": 1 << 64},
                          {"id": absent_id}, {"id": 1, "extra": "x"}):
                self._assert_error("GET", path, query=query)
        self._assert_error(
            "POST", "/api/query-participant", query={"unknown": "x"},
        )
        self._assert_error(
            "POST", "/api/query-command/1", query={"participant": 2},
        )
        self._assert_error("POST", "/api/query-reply/1", query={"command": 2})

    def _check_authorization(self) -> None:
        """Проверить отсутствие и разные неверные формы Basic-заголовка."""
        headers = ("", "Bearer token", "Basic !", "Basic YQ==", "Basic /w==")
        for header in headers:
            try:
                self.client.request(
                    "POST", "/api/query-report", authorization=header,
                )
            except ApiError as error:
                assert error.status == expected_unauthorized
            else:
                raise AssertionError("Доступ без авторизации разрешён")

    @rule(name=text_values)
    def participant_insert(self, name: str) -> None:
        """Сгенерировать создание нового участника."""
        self._add_participant(name)

    @rule(text=text_values, index=st.integers(min_value=0, max_value=100),
          age=st.sampled_from((0, 479, 480, 481)))
    def command_insert(self, text: str, index: int, age: int) -> None:
        """Сгенерировать задачу участника, включая границу восьми минут."""
        participants = self.model.tables["participant"]
        participant = participants[index % len(participants)]["id"]
        self._add_command(text, participant, age)

    @rule(index=st.integers(min_value=0, max_value=100))
    def repeated_command(self, index: int) -> None:
        """Проверить повторную генерацию, кэш и удаление повторов отчёта."""
        commands = self.model.tables["command"]
        command = commands[index % len(commands)]
        self._add_command(command["parameter"], command["participant"], 0)

    def _add_pending_command(self, text: str) -> None:
        """Проверить немедленный ответ API и LEFT JOIN до готовности SVG."""
        started, release = threading.Event(), threading.Event()
        data = {
            "participant": 1, "description": "pending " + text, "tags": "mbt",
            "parameter": "pending {} {}".format(
                text, len(self.model.tables["command"]),
            ),
        }

        def delayed_generation(value: str) -> str:
            """Удержать задачу, пока API проверяет незавершённое состояние."""
            started.set()
            release.wait(timeout=10)
            return expected_svg

        runner = self.live.application.tasks
        with patch.object(runner, "_generate", side_effect=delayed_generation):
            try:
                actual = self.client.command_insert(data)
                expected = self.model.insert("command", data)
                self._assert_record(actual, expected)
                assert started.wait(timeout=2)
                self.model.inspect("command", expected["id"])["spawned"] = 1
                self._check_reads()
            finally:
                release.set()
            reply = self.client.wait_for_reply(expected["id"])
            self._assert_record(reply, self.model.finish(expected["id"]))

    @rule(text=text_values)
    def pending_command(self, text: str) -> None:
        """Сгенерировать проверки незавершённой асинхронной задачи."""
        self._add_pending_command(text)

    @rule(step=st.sampled_from((0, 1, 479, 480, 481)))
    def advance_time(self, step: int) -> None:
        """Сдвинуть часы и проверить истечение восьмиминутного интервала."""
        self.model.now += step
        self.live.clock.value = self.model.now
        self._check_reads()

    @rule()
    def read_and_query(self) -> None:
        """Сравнить чтение и фильтрацию всех отношений."""
        self._check_reads()
        assert self.client.participant_query({"locale": "absent"}) == []
        participant = self.model.tables["participant"][0]
        expected = self.model.query("participant", {"id": participant["id"]})
        assert self.client.participant_query(
            {"id": participant["id"]},
        ) == expected
        assert self.client.command_query(
            participant["id"], {"tags": "absent"},
        ) == []
        assert self.client.reply_query(1, {"status": "absent"}) == []

    @rule()
    def invalid_foreign_key(self) -> None:
        """Отклонить создание команды с несуществующим участником."""
        try:
            self.client.command_insert({
                "participant": absent_id, "parameter": "test",
                "description": "invalid", "tags": "mbt",
            })
        except ApiError as error:
            assert error.status == expected_ok
        else:
            raise AssertionError("Неправильная связь принята")

    def teardown(self) -> None:
        """Закрыть тестовый сервер после сгенерированного сценария."""
        self.live.close()
        super().teardown()


api_test_case = ApiMachine.TestCase

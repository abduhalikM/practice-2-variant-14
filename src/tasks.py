"""Асинхронный запуск CLI через subprocess и сохранение Reply."""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.config import Settings
from src.schema import Record
from src.storage import Storage


test_svg = '<svg xmlns="http://www.w3.org/2000/svg" data-test="true"/>'
milliseconds = 1000
successful_exit = 0


class TaskRunner:
    """Выполняет задания последовательно в отдельном рабочем потоке."""

    def __init__(self, storage: Storage, settings: Settings) -> None:
        """Создать очередь, кэш и параметры запуска CLI."""
        self.storage = storage
        self.settings = settings
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.cache: dict[str, str] = {}
        self.futures = {}

    def submit(self, command: Record) -> None:
        """Поставить команду в очередь, не ожидая генерации SVG."""
        self.futures[command["id"]] = self.executor.submit(self._run, command)

    def resume_pending(self) -> None:
        """После запуска сервера восстановить задания без ответа."""
        completed = {row["command"] for row in self.storage.query("reply")}
        for command in self.storage.query("command"):
            if command["id"] not in completed:
                self.submit(command)

    def _generate(self, text: str) -> str:
        """В тестовом режиме вернуть заглушку, иначе запустить процесс."""
        if self.settings.test_mode:
            return test_svg
        result = subprocess.run(
            [sys.executable, "-B", "-m", "src.cli"], input=text,
            capture_output=True, encoding="utf-8",
            timeout=self.settings.timeout,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if result.returncode != successful_exit:
            raise ValueError(result.stderr.strip() or "Ошибка генератора")
        return result.stdout

    def _run(self, command: Record) -> None:
        """Обработать команду и сохранить успешный или ошибочный ответ."""
        started = time.monotonic()
        reply = {
            "command": command["id"], "status": "success",
            "exception": "", "cache_hit": 0, "response": "",
        }
        self.storage.mark_spawned(command["id"])
        try:
            text = command["parameter"]
            if text in self.cache:
                reply.update(response=self.cache[text], cache_hit=1)
            else:
                reply["response"] = self._generate(text)
                self.cache[text] = reply["response"]
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            reply.update(status="failed", exception=str(error))
        reply["duration"] = int((time.monotonic() - started) * milliseconds)
        self.storage.insert("reply", reply)

    def wait(self, command_id: int) -> None:
        """Дождаться конкретной задачи при проверках приложения."""
        self.futures[command_id].result(timeout=self.settings.timeout + 5)

    def close(self) -> None:
        """Дождаться задач перед закрытием базы данных."""
        self.executor.shutdown(wait=True)

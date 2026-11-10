"""Независимая эталонная модель: списки вместо TinyDB и SQL."""


expected_svg = '<svg xmlns="http://www.w3.org/2000/svg" data-test="true"/>'
report_interval = 480


class ReferenceModel:
    """Предсказывает записи, связи, кэш и результат формулы (14)."""

    def __init__(self, now: int) -> None:
        """Создать пустые отношения и кэш эталонной модели."""
        self.now = now
        self.tables = {"participant": [], "command": [], "reply": []}
        self.cached = set()

    def insert(self, entity: str, data: dict) -> dict:
        """Назначить независимый id и сохранить копию ожидаемой записи."""
        row = dict(data)
        row.setdefault("created", self.now)
        row["id"] = len(self.tables[entity]) + 1
        if entity == "command":
            row["spawned"] = 0
        self.tables[entity].append(row)
        return dict(row)

    def finish(self, command_id: int) -> dict:
        """Предсказать завершение тестовой задачи и признак кэша."""
        command = self.inspect("command", command_id)
        command["spawned"] = 1
        text = command["parameter"]
        reply = self.insert("reply", {
            "command": command_id, "status": "success", "exception": "",
            "response": expected_svg, "cache_hit": int(text in self.cached),
            "duration": 0,
        })
        self.cached.add(text)
        return reply

    def inspect(self, entity: str, record_id: int) -> dict:
        """Найти ожидаемую запись обычным перебором списка."""
        return next(
            row for row in self.tables[entity] if row["id"] == record_id
        )

    def query(self, entity: str, filters: dict) -> list[dict]:
        """Выполнить поиск в эталонной модели без кода приложения."""
        return [
            dict(row) for row in self.tables[entity]
            if all(row[key] == value for key, value in filters.items())
        ]

    def report(self) -> set[tuple]:
        """Построить эталонную проекцию вложенным перебором отношений."""
        rows = set()
        for command in self.tables["command"]:
            if command["created"] <= self.now - report_interval:
                continue
            participant = self.inspect("participant", command["participant"])
            matching = self.query("reply", {"command": command["id"]})
            for reply in matching or [{"response": None}]:
                rows.add((
                    command["description"], participant["ip"],
                    reply["response"],
                ))
        return rows

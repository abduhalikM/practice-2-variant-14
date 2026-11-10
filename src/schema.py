"""Поля ER-диаграммы и проверка записей Participant, Command и Reply."""

from typing import Any

from src.qr import minimum_control, validate_text


Record = dict[str, Any]
minimum_id = 1
minimum_time = 0
minimum_integer = -(1 << 63)
maximum_integer = (1 << 63) - 1
fields = {
    "participant": {
        "id": int, "created": int, "ip": str,
        "locale": str, "user_agent": str,
    },
    "command": {
        "id": int, "created": int, "parameter": str, "participant": int,
        "description": str, "tags": str, "spawned": int,
    },
    "reply": {
        "id": int, "created": int, "response": str, "status": str,
        "exception": str, "command": int, "cache_hit": int, "duration": int,
    },
}
required_fields = {
    "participant": {"ip", "locale", "user_agent"},
    "command": {"parameter", "participant", "description", "tags"},
    "reply": {"response", "status", "exception", "command", "cache_hit",
              "duration"},
}


def convert_value(value: Any, expected: type) -> Any:
    """Проверить строку либо преобразовать целое значение из HTTP/XML."""
    if expected is int:
        if type(value) not in (str, int):
            raise ValueError("Ожидается целое число")
        number = int(value)
        if not minimum_integer <= number <= maximum_integer:
            raise ValueError("Целое число выходит за диапазон SQLite")
        return number
    if not isinstance(value, str):
        raise ValueError("Ожидается строка")
    if any(ord(char) < minimum_control and char not in "\t\r\n"
           for char in value):
        raise ValueError("Недопустимый символ XML")
    return value


def clean_fields(entity: str, data: Record) -> Record:
    """Отклонить неизвестные поля и преобразовать значения по схеме."""
    if entity not in fields or not isinstance(data, dict):
        raise ValueError("Неизвестная сущность или неверные данные")
    if set(data) - fields[entity].keys():
        raise ValueError("Неизвестные поля записи")
    return {
        key: convert_value(value, fields[entity][key])
        for key, value in data.items()
    }


def prepare_record(entity: str, data: Record, now: int) -> Record:
    """Проверить обязательные поля и добавить время создания."""
    record = clean_fields(entity, data)
    if "id" in record:
        raise ValueError("Идентификатор назначается автоматически")
    missing = required_fields[entity] - record.keys()
    if missing:
        raise ValueError("Не заполнены поля: " + ", ".join(sorted(missing)))
    record.setdefault("created", now)
    if record["created"] < minimum_time:
        raise ValueError("Время создания не может быть отрицательным")
    if entity == "command":
        validate_text(record["parameter"])
        record["spawned"] = 0
    return record

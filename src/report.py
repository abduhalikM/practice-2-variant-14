"""Формула (14): внешние соединения, отбор по времени и проекция."""

from src.schema import Record


recent_interval = 8 * 60


def build_report(
    participants: list[Record], commands: list[Record],
    replies: list[Record], now: int,
) -> list[Record]:
    """Получить уникальные description, ip и response за восемь минут."""
    participant_by_id = {row["id"]: row for row in participants}
    result = []
    for command in commands:
        if command["created"] <= now - recent_interval:
            continue
        participant = participant_by_id.get(command["participant"])
        responses = [
            row["response"] for row in replies
            if row["command"] == command["id"]
        ]
        for response in responses or [None]:
            row = {
                "description": command["description"],
                "ip": participant["ip"] if participant else None,
                "response": response,
            }
            if row not in result:
                result.append(row)
    return result

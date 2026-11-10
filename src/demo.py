"""Демонстрация всех девяти обработчиков и готового SVG через API."""

from pathlib import Path

from src.client import ApiClient, ApiError, configured_client
from src.config import load_settings, parse_options


def demonstrate(client: ApiClient) -> None:
    """Создать участника, отправить задачу и получить результат."""
    participant = client.participant_insert({
        "ip": "127.0.0.1", "locale": "ru-RU", "user_agent": "Demo",
    })
    print("Участник:", client.participant_inspect(participant["id"]))
    print("Поиск участников:", client.participant_query({"locale": "ru-RU"}))
    command = client.command_insert({
        "participant": participant["id"], "parameter": "https://www.mirea.ru",
        "description": "QR-код сайта МИРЭА", "tags": "demo",
    })
    print("Задача принята:", command)
    reply = client.wait_for_reply(command["id"])
    print("Команда:", client.command_inspect(command["id"]))
    print("Команд участника:", len(client.command_query(participant["id"])))
    print("Ответов команды:", len(client.reply_query(command["id"])))
    saved = client.reply_inspect(reply["id"])
    if saved["status"] != "success":
        raise RuntimeError(saved["exception"])
    destination = Path("output/demo.svg")
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(saved["response"], encoding="utf-8")
    print("SVG сохранён:", destination)
    print("Строк отчёта:", len(client.report_query()))
    try:
        client.participant_inspect(-1)
    except ApiError as error:
        print("Ожидаемая ошибка:", error)


def main() -> None:
    """Выполнить демонстрацию с настройками из config.ini."""
    arguments = parse_options("Демонстрация QR API")
    demonstrate(configured_client(load_settings(arguments.config)))


if __name__ == "__main__":
    main()

"""Интерактивная работа с HTTP API через объект client."""

import code

from src.client import configured_client
from src.config import load_settings, parse_options


def main() -> None:
    """Открыть консоль API-клиента после запуска сервера."""
    arguments = parse_options("Интерактивный HTTP-клиент")
    client = configured_client(load_settings(arguments.config))
    message = (
        "Клиент доступен как client. Сначала запустите сервер.\n"
        "Пример: client.participant_query()\n"
        "Выход: exit()."
    )
    code.interact(banner=message, local={"client": client})


if __name__ == "__main__":
    main()

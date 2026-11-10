# HTTP API — практическая №2, вариант 14

Тема: асинхронная генерация QR-кодов в SVG. Реализованы три отдельных
сценария запуска: CLI, Bottle + TinyDB, Bottle + SQLite.

## Структура

| Файл | Назначение |
|---|---|
| `src/qr.py`, `src/cli.py` | Проверка текста и генерация SVG через stdin/stdout |
| `src/demo_cli.py` | Три примера первого этапа |
| `src/schema.py`, `src/storage.py` | Схема, типы, внешние ключи, общий интерфейс |
| `src/file_store.py` | Файловая СУБД TinyDB второго этапа |
| `src/sqlite_store.py` | SQLite третьего этапа, только SQL без ORM |
| `src/report.py` | Формула (14) для файловой модели |
| `src/factory.py` | Выбор хранилища |
| `src/api.py`, `src/security.py` | Девять маршрутов, XML и Basic Auth |
| `src/xml_codec.py` | Кодирование XML и защита от внешних сущностей |
| `src/tasks.py` | Очередь, subprocess, кэш и сохранение ответа |
| `src/server.py`, `src/config.py` | Запуск сервера и настройки |
| `src/client.py`, `src/repl.py` | HTTP-клиент и интерактивная консоль |
| `src/demo.py` | Демонстрация всех маршрутов |
| `src/checks.py`, `src/coverage_check.py` | Оформление и покрытие обработчиков |
| `tests/test_mbt.py`, `tests/reference.py` | Hypothesis и независимая модель |

## Методы клиента и обработчики

Параметр `data` — словарь полей записи. Параметр `filters` — необязательный
словарь точных совпадений полей. Без фильтров возвращаются все записи
в пределах указанного участника или команды. Поиск использует строку URL,
в том числе у POST-запросов. Чтение использует параметр `id`.

| Метод клиента | HTTP | Маршрут | Результат |
|---|---|---|---|
| `participant_insert(data)` | POST | `/api/insert-participant` | Участник |
| `participant_query(filters=None)` | POST | `/api/query-participant` | Список участников |
| `participant_inspect(record_id)` | GET | `/api/inspect-participant?id=...` | Участник |
| `command_insert(data)` | POST | `/api/insert-command` | Принятая команда |
| `command_query(participant, filters=None)` | POST | `/api/query-command/:participant` | Команды участника |
| `command_inspect(record_id)` | GET | `/api/inspect-command?id=...` | Команда |
| `reply_query(command, filters=None)` | POST | `/api/query-reply/:command` | Ответы команды |
| `reply_inspect(record_id)` | GET | `/api/inspect-reply?id=...` | Ответ |
| `report_query()` | POST | `/api/query-report` | Строки формулы (14) |

Дополнительный метод `wait_for_reply(command, timeout=20)` опрашивает
`reply_query` до получения ответа. При превышении времени он вызывает
`TimeoutError`. `request(method, path, body=None, query=None,
authorization=None)` позволяет выполнить низкоуровневый запрос.

Клиент создаётся как `ApiClient(base_url, username, password, timeout=10)`.
Ошибки HTTP и операций представлены исключением `ApiError` с полем `status`.

## Поля записей

- Participant: `id: int`, `created: int`, `ip: str`, `locale: str`,
  `user_agent: str`.
- Command: `id: int`, `created: int`, `parameter: str`, `participant: int`,
  `description: str`, `tags: str`, `spawned: int`.
- Reply: `id: int`, `created: int`, `response: str`, `status: str`,
  `exception: str`, `command: int`, `cache_hit: int`, `duration: int`.

При создании участника обязательны `ip`, `locale`, `user_agent`.
При создании команды обязательны `parameter`, `participant`, `description`,
`tags`. `parameter` — текст для QR-кода, от 1 непустого текста до 2000 байт
UTF-8. Символы управления, недопустимые в XML, отклоняются.

`id` назначается автоматически; передавать его при создании нельзя.
`created` — Unix-время в секундах, по умолчанию берётся текущее время.
Его можно указать явно, в том числе для проверки восьмиминутного интервала.
Признак `spawned` устанавливает сервер: 0 при приёме, 1 при запуске обработки.
Один участник имеет несколько команд, команда ссылается на одного участника.
Одна команда может иметь несколько Reply по схеме; обработчик задачи создаёт
один итоговый ответ. Создание Reply через HTTP не предусмотрено таблицей 14.

## Выполнение задач

`command_insert` сохраняет команду и немедленно возвращает её, пока отдельный
поток обрабатывает очередь. Генератор вызывается через `subprocess.run`
без shell: параметр передаётся в stdin, SVG читается из stdout.
Одновременно выполняется одна задача; остальные остаются в очереди.

Успех: `status=success`, SVG в `response`, пустой `exception`.
Ошибка процесса или тайм-аут: `status=failed`, пустой `response`, описание
в `exception`. `duration` измеряется в миллисекундах. Для повторного текста
используется кэш текущего запуска, тогда `cache_hit=1`; иначе он равен 0.

В тестовом режиме процесс не запускается. Возвращается SVG-заглушка с
`data-test="true"`; она не является QR-кодом. При обычном завершении сервер
ожидает задачи перед закрытием базы. После запуска задания без Reply
возвращаются в очередь. Выполнение после аварийного завершения имеет
семантику повторного запуска, а не гарантию exactly-once.

## XML и авторизация

Тело создания записи имеет корень `request`. Пример участника:

```xml
<request>
  <ip>127.0.0.1</ip>
  <locale>ru-RU</locale>
  <user_agent>Demo</user_agent>
</request>
```

Пример команды, содержащей специальные символы XML:

```xml
<request>
  <participant>1</participant>
  <parameter>https://example.com/?a=1&amp;b=2</parameter>
  <description>QR-код ссылки</description>
  <tags>demo</tags>
</request>
```

Ответ имеет корень `response`, поля `ok` и `result` либо `ok` и `error`.
Атрибуты `type` различают `dict`, `list`, `str`, `int`, `bool`, `null`.
Элементы списка называются `item`. SVG внутри `response` передаётся
экранированной строкой; клиент восстанавливает исходный SVG-текст.

Авторизованные операции возвращают HTTP 200. Ошибка данных также имеет
код 200, но `ok=false` и описание в `error`. Без правильной пары логин/пароль
возвращается 401 и `WWW-Authenticate: Basic realm="qr-api", charset="UTF-8"`.
Клиент отправляет UTF-8 пару в заголовке Basic по RFC 7617.
Неизвестный маршрут даёт 404, неправильный HTTP-метод — 405, также с XML.
Максимальное тело запроса — 1 МиБ. Внешние сущности XML запрещены.

## Настройки

Файл `config.ini`:

- `server.host`, `server.port` — адрес и порт, по умолчанию 127.0.0.1:8080.
- `server.username`, `server.password` — Basic-авторизация: student / qr-demo.
- `storage.backend` — `tinydb` для этапа 2, `sqlite` для этапа 3.
- `storage.directory` — папка базы относительно файла конфигурации.
- `tasks.test_mode` — заглушка вместо процесса, по умолчанию false.
- `tasks.timeout` — максимальное время subprocess в секундах, по умолчанию 15.

Параметр запуска `--config` выбирает другой INI-файл. Параметры `--backend`
и `--test-mode` переопределяют настройки сервера. TinyDB использует
`data/jobs.json`, SQLite — `data/jobs.sqlite3`; это разные базы.

## Формула (14)

Сопоставление `Participant.id = Command.participant` сохраняет команды,
затем левое внешнее соединение по `Command.id = Reply.command` сохраняет
команду без ответа с `response=None`. Фильтр строгий:
`Command.created > now - 480`. Проекция возвращает `description`, `ip`,
`response` и удаляет одинаковые результирующие строки.

TinyDB вычисляет формулу в `build_report`. SQLite выполняет `SELECT DISTINCT`
с двумя `LEFT JOIN`, начиная с Command. Это эквивалент записи
`(Participant RIGHT JOIN Command) LEFT JOIN Reply` и работает в том числе
в версиях SQLite без поддержки RIGHT JOIN.

## Тестирование

`RuleBasedStateMachine` генерирует действия и данные. API проверяется
настоящим HTTP-клиентом, а ожидаемые записи и отчёт вычисляются независимой
моделью на списках. Время управляется тестовыми часами. Проверяются также
состояние до завершения задачи, внешнее соединение без Reply, повторные
задачи, кэш, уникальность проекции, фильтры, неверные XML и Basic-заголовки.

Команда `python -m src.coverage_check --backend tinydb` измеряет этап 2,
а `--backend sqlite` — этап 3. Обе запускают только `tests.test_mbt`, без
обычных unit-тестов. Измеряется покрытие ветвей. Для `src/api.py` установлен
порог 100%; полный отчёт по исходникам находится в HTML и JSON.
В проекте оставлена только машина состояний Hypothesis, обычных классов
unit-тестов нет. `ApiMachine.TestCase` — автоматически созданный Hypothesis
адаптер запуска через unittest; он не содержит написанных вручную unit-тестов.
Команда запуска выполняет сгенерированные действия MBT и сравнивает HTTP API
с независимой моделью. Реальный генератор показывается тремя CLI-примерами
и обычной демонстрацией API с выключенным тестовым режимом.

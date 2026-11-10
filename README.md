Практическая №2, вариант 14. ИКБО-71-24.
HTTP API для асинхронной генерации QR-кодов в SVG.

Подготовка

Нужен Python 3.11 или новее. Команды выполняются из папки проекта.
Команды с client вводятся только после появления >>> в интерактивной консоли.

py -m venv .venv - создаёт виртуальное окружение.

.venv\Scripts\python.exe -m pip install -r requirements-dev.txt - устанавливает зависимости.

Первый этап — генератор QR-кодов

Утилита читает текст из стандартного ввода и выдаёт SVG в стандартный вывод.
При ошибке сообщение направляется в stderr, код завершения равен 1.

.venv\Scripts\python.exe -B -m src.demo_cli - запускает три примера: текст, URL и кириллицу.

Результаты находятся в output/example-1.svg, example-2.svg и example-3.svg.

В PowerShell: 'Hello, QR!' | .venv\Scripts\python.exe -B -m src.cli - передаёт свой текст генератору.

Второй этап — HTTP API и файловая СУБД

Сервер Bottle принимает XML, ставит задачи в фоновую очередь и запускает CLI
через subprocess. Участники, команды и ответы сохраняются в TinyDB на диске.

.venv\Scripts\python.exe -B -m src.server --backend tinydb - запускает сервер в первом терминале.

.venv\Scripts\python.exe -B -m src.demo - во втором терминале показывает все 9 методов и сохраняет output/demo.svg.

.venv\Scripts\python.exe -B -m src.repl - открывает интерактивный HTTP-клиент во втором терминале.

p = client.participant_insert({"ip": "127.0.0.1", "locale": "ru-RU", "user_agent": "Demo"}) - создаёт участника.

client.participant_inspect(p["id"]) - читает участника по id.

c = client.command_insert({"participant": p["id"], "parameter": "https://www.mirea.ru", "description": "QR", "tags": "demo"}) - принимает задачу, не ожидая генерации.

r = client.wait_for_reply(c["id"]) - получает готовый ответ отдельными HTTP-запросами.

r["response"] - показывает SVG; r["status"] показывает success или failed.

client.report_query() - показывает отчёт по формуле за последние 8 минут.

client.participant_inspect(-1) - показывает ожидаемую ошибку.

exit() - закрывает клиент. Ctrl+C в первом терминале останавливает сервер.

.venv\Scripts\python.exe -B -m src.server --backend tinydb --test-mode - запускает сервер с заглушкой вместо реальной генерации.

.venv\Scripts\python.exe -B -m src.coverage_check --backend tinydb - запускает только MBT и создаёт отчёт второго этапа в reports/tinydb/index.html.

Третий этап — SQLite

Тот же API работает с SQLite через SQL-запросы. Данные сохраняются после
перезапуска. Перед сменой хранилища остановить предыдущий сервер через Ctrl+C.

.venv\Scripts\python.exe -B -m src.server --backend sqlite - запускает третий этап в первом терминале.

.venv\Scripts\python.exe -B -m src.demo - во втором терминале повторяет демонстрацию с SQLite.

.venv\Scripts\python.exe -B -m src.coverage_check --backend sqlite - создаёт отчёт третьего этапа в reports/sqlite/index.html.

Проверки и настройки

.venv\Scripts\python.exe -B -m unittest tests.test_mbt -v - запускает только MBT с SQLite; сценарии генерирует Hypothesis.

.venv\Scripts\python.exe -B -m src.checks - проверяет ограничения ЦАП и flake8.

run.bat - запускает сервер; по умолчанию используется SQLite. В Linux — sh run.sh.

Адрес по умолчанию: http://127.0.0.1:8080. Basic-авторизация: student / qr-demo.
Адрес, порт, логин, пароль, СУБД, папка данных и тайм-аут задаются в config.ini.
Описание всех методов, XML и структуры проекта находится в docs/API.md.
Сборка не требуется. Базы данных, SVG, окружение и отчёты не добавляются в Git.

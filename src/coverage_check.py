"""Отчёт покрытия HTTP API только сгенерированными MBT-сценариями."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Запустить MBT выбранного этапа и сформировать отчёты coverage."""
    parser = argparse.ArgumentParser(description="Покрытие HTTP-обработчиков")
    parser.add_argument("--backend", choices=("tinydb", "sqlite"),
                        default="sqlite")
    backend = parser.parse_args().backend
    root = Path(__file__).resolve().parent.parent
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    data_file = ".coverage-" + backend
    environment = dict(os.environ, QR_TEST_BACKEND=backend)
    python = [sys.executable, "-B", "-m", "coverage"]
    commands = (
        ["run", "--branch", "--source=src", "--data-file=" + data_file,
         "-m", "unittest", "tests.test_mbt", "-v"],
        ["report", "--data-file=" + data_file, "--include=src/api.py",
         "--fail-under=100", "-m"],
        ["html", "--data-file=" + data_file,
         "-d", str(reports / backend)],
        ["json", "--data-file=" + data_file,
         "-o", str(reports / (backend + ".json"))],
    )
    for arguments in commands:
        subprocess.run(
            python + arguments, cwd=root, env=environment, check=True,
        )
    print("HTML-отчёт:", reports / backend / "index.html")


if __name__ == "__main__":
    main()

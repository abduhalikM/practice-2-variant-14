"""Три примера запуска CLI с сохранением полученных SVG."""

import subprocess
import sys
from pathlib import Path


examples = ("Hello, QR!", "https://www.mirea.ru", "Привет, МИРЭА!")


def main() -> None:
    """Передать три текста в stdin генератора и сохранить его stdout."""
    output = Path("output")
    output.mkdir(exist_ok=True)
    for number, text in enumerate(examples, start=1):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "src.cli"],
            input=text, capture_output=True, encoding="utf-8", check=True,
        )
        destination = output / "example-{}.svg".format(number)
        destination.write_text(result.stdout, encoding="utf-8")
        print("{} -> {}".format(text, destination))


if __name__ == "__main__":
    main()

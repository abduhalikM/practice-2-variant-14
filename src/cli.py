"""Утилита первого этапа: текст из stdin, QR-код в SVG через stdout."""

import sys

from src.qr import generate_svg


def main() -> int:
    """Прочитать UTF-8 текст и вывести SVG либо ошибку в stderr."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        text = sys.stdin.read().rstrip("\r\n")
        sys.stdout.write(generate_svg(text))
        return 0
    except (ValueError, UnicodeError) as error:
        print("Ошибка: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

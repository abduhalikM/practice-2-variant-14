"""Проверка текста и генерация стандартного QR-кода в формате SVG."""

import io

import segno


max_text_bytes = 2000
minimum_control = 32
svg_namespace = "http://www.w3.org/2000/svg"


def validate_text(text: str) -> str:
    """Проверить непустой UTF-8 текст, подходящий для QR-кода."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Нужен непустой текст для QR-кода")
    if len(text.encode("utf-8")) > max_text_bytes:
        raise ValueError("Текст превышает 2000 байт UTF-8")
    if any(ord(char) < minimum_control and char not in "\t\r\n"
           for char in text):
        raise ValueError("Текст содержит управляющие символы")
    return text


def generate_svg(text: str) -> str:
    """Преобразовать текст в SVG без создания файлов на диске."""
    qr = segno.make_qr(
        validate_text(text), error="m", encoding="utf-8", eci=True,
    )
    output = io.BytesIO()
    qr.save(output, kind="svg", scale=8, border=4, xmldecl=True)
    return output.getvalue().decode("utf-8")

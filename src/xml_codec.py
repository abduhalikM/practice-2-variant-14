"""Безопасные XML-запросы и типизированные XML-ответы HTTP API."""

from xml.etree.ElementTree import Element, SubElement, tostring

from defusedxml.ElementTree import fromstring

from src.schema import Record


max_request_bytes = 1024 * 1024


def encode_request(data: Record) -> bytes:
    """Сформировать XML с плоскими полями запроса."""
    root = Element("request")
    for key, value in data.items():
        SubElement(root, key).text = str(value)
    return tostring(root, encoding="utf-8", xml_declaration=True)


def decode_request(payload: bytes) -> Record:
    """Прочитать плоский XML без DTD, сущностей и повторяющихся полей."""
    root = fromstring(payload)
    if root.tag != "request" or root.attrib:
        raise ValueError("Ожидается корневой элемент request без атрибутов")
    result = {}
    for child in root:
        if child.tag in result or child.attrib or list(child):
            raise ValueError("Повторяющееся поле или вложенный XML")
        result[child.tag] = child.text or ""
    return result


def _write_value(element: Element, value: object) -> None:
    """Записать словарь, список или скаляр в XML-элемент."""
    if isinstance(value, dict):
        element.set("type", "dict")
        for key, child in value.items():
            _write_value(SubElement(element, key), child)
    elif isinstance(value, list):
        element.set("type", "list")
        for child in value:
            _write_value(SubElement(element, "item"), child)
    elif value is None:
        element.set("type", "null")
    elif isinstance(value, bool):
        element.set("type", "bool")
        element.text = "true" if value else "false"
    else:
        element.set("type", "int" if isinstance(value, int) else "str")
        element.text = str(value)


def encode_response(data: Record) -> bytes:
    """Сериализовать ответ, сохраняя SVG как экранированный текст."""
    root = Element("response")
    _write_value(root, data)
    return tostring(root, encoding="utf-8", xml_declaration=True)


def _read_value(element: Element) -> object:
    """Восстановить типизированное значение из XML-ответа."""
    kind = element.get("type")
    if kind == "dict":
        return {child.tag: _read_value(child) for child in element}
    if kind == "list":
        return [_read_value(child) for child in element]
    if kind == "null":
        return None
    if kind == "bool":
        return element.text == "true"
    if kind == "int":
        return int(element.text)
    if kind == "str":
        return element.text or ""
    raise ValueError("Неизвестный тип XML-ответа")


def decode_response(payload: bytes) -> Record:
    """Прочитать типизированный объект ответа API."""
    root = fromstring(payload)
    if root.tag != "response" or root.get("type") != "dict":
        raise ValueError("Некорректный XML-ответ")
    return _read_value(root)

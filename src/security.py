"""HTTP Basic по RFC 7617 и единый XML-формат ответов."""

import base64
import binascii
import hmac
from functools import wraps
from xml.etree.ElementTree import ParseError

from bottle import request, response
from defusedxml.common import DefusedXmlException

from src.config import Settings
from src.xml_codec import encode_response


unauthorized_status = 401
ok_status = 200
xml_content_type = "application/xml; charset=utf-8"


def authorized(header: str, settings: Settings) -> bool:
    """Проверить схему Basic и пару UTF-8 логин:пароль."""
    try:
        scheme, token = header.split(None, 1)
        if scheme.lower() != "basic":
            return False
        credentials = base64.b64decode(token, validate=True).decode("utf-8")
        username, password = credentials.split(":", 1)
        valid_user = hmac.compare_digest(
            username.encode("utf-8"), settings.username.encode("utf-8"),
        )
        valid_password = hmac.compare_digest(
            password.encode("utf-8"), settings.password.encode("utf-8"),
        )
        return valid_user and valid_password
    except (ValueError, UnicodeError, binascii.Error):
        return False


def protect(callback: object, settings: Settings) -> object:
    """Обернуть обработчик проверкой авторизации и обработкой ошибок."""
    @wraps(callback)
    def wrapped(**arguments: object) -> bytes:
        """Вернуть XML и 401 либо XML-результат с кодом 200."""
        response.content_type = xml_content_type
        response.set_header("Cache-Control", "no-store")
        if not authorized(request.get_header("Authorization", ""), settings):
            response.status = unauthorized_status
            response.set_header(
                "WWW-Authenticate", 'Basic realm="qr-api", charset="UTF-8"',
            )
            return encode_response({"ok": False, "error": "Unauthorized"})
        response.status = ok_status
        try:
            result = callback(**arguments)
            return encode_response({"ok": True, "result": result})
        except (
            ValueError, KeyError, ParseError, DefusedXmlException,
        ) as error:
            return encode_response({"ok": False, "error": str(error)})
    return wrapped


def http_error(error: object) -> bytes:
    """Вернуть XML вместо HTML для неизвестного маршрута или метода."""
    response.content_type = xml_content_type
    return encode_response({"ok": False, "error": str(error.status)})

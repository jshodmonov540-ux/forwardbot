import io
import logging
from core.logger import SensitiveDataFilter


def test_sensitive_data_filter_masks_card_numbers():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))

    test_logger = logging.getLogger("test_security_card")
    test_logger.handlers = [handler]
    test_logger.setLevel(logging.INFO)

    test_logger.info("Foydalanuvchi kartasi: 8600 1234 5678 9012 orqali amal")
    output = stream.getvalue()

    assert "8600 1234 5678 9012" not in output
    assert "[CARD_MASKED]" in output


def test_sensitive_data_filter_masks_phone_numbers():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))

    test_logger = logging.getLogger("test_security_phone")
    test_logger.handlers = [handler]
    test_logger.setLevel(logging.INFO)

    test_logger.info("Bog'lanish uchun raqam: +998901234567")
    output = stream.getvalue()

    assert "+998901234567" not in output
    assert "[PHONE_MASKED]" in output


def test_sensitive_data_filter_masks_bot_token():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(logging.Formatter("%(message)s"))

    test_logger = logging.getLogger("test_security_token")
    test_logger.handlers = [handler]
    test_logger.setLevel(logging.INFO)

    test_logger.info("Ulanish amalga oshirildi: 123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ123456789")
    output = stream.getvalue()

    assert "123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ123456789" not in output
    assert "[TOKEN_MASKED]" in output

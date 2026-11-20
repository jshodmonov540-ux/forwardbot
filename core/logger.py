import logging
import re
import sys
from typing import Any
from core.config import settings

CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
PHONE_PATTERN = re.compile(r"(?:\+?998|8)[\s-]?(?:9\d|33|88|77|50)[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
TOKEN_PATTERN = re.compile(r"\d{8,11}:[a-zA-Z0-9_-]{30,45}")


class SensitiveDataFilter(logging.Filter):
    """
    Sezgir ma'lumotlarni (telefon, karta, bot token) logdan tozalovchi filtr.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            msg = TOKEN_PATTERN.sub("[TOKEN_MASKED]", msg)
            msg = CARD_PATTERN.sub("[CARD_MASKED]", msg)
            msg = PHONE_PATTERN.sub("[PHONE_MASKED]", msg)
            record.msg = msg

        if record.args:
            cleaned_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    arg = TOKEN_PATTERN.sub("[TOKEN_MASKED]", arg)
                    arg = CARD_PATTERN.sub("[CARD_MASKED]", arg)
                    arg = PHONE_PATTERN.sub("[PHONE_MASKED]", arg)
                cleaned_args.append(arg)
            record.args = tuple(cleaned_args)

        return True


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("forwardbot")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(SensitiveDataFilter())
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Aiogram va SQLAlchemy loglarini ham himoyalash
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        h.addFilter(SensitiveDataFilter())

    return logger


logger = setup_logger()

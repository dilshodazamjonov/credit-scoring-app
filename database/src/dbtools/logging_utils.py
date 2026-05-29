from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Iterator

DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "event=%(message)s"
)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: str | None = None) -> None:
    resolved_level = (level or os.getenv("DBTOOLS_LOG_LEVEL", DEFAULT_LOG_LEVEL)).upper()
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(resolved_level)
        return

    logging.basicConfig(
        level=resolved_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


@contextmanager
def log_step(logger: logging.Logger, event: str, **fields: object) -> Iterator[None]:
    logger.info("%s %s", event, _serialize_fields(fields))
    started_at = time.perf_counter()
    try:
        yield
    except Exception:
        logger.exception(
            "%s_failed %s",
            event,
            _serialize_fields({**fields, "duration_ms": _duration_ms(started_at)}),
        )
        raise
    logger.info(
        "%s_done %s",
        event,
        _serialize_fields({**fields, "duration_ms": _duration_ms(started_at)}),
    )


def _duration_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)


def _serialize_fields(fields: dict[str, object]) -> str:
    return " ".join(f"{key}={_quote(value)}" for key, value in fields.items())


def _quote(value: object) -> str:
    text = str(value)
    if not text or any(char.isspace() for char in text):
        return f'"{text}"'
    return text

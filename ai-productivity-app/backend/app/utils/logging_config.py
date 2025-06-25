"""Enhanced logging configuration with request-ID support (strict mode)."""

from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger  # strict import – must exist

# Local import (relative to the 'app' package)
from ..middleware.correlation_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Inject the current request ID (or a placeholder) into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        record.request_id = get_request_id() or "no-request-id"
        return True


def setup_logging(*, json_logs: bool = False, log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with optional JSON output and request-ID enrichment.

    Args:
        json_logs: Emit logs in JSON format when True.
        log_level: Root logger threshold (e.g. "DEBUG", "INFO").
    Returns:
        The configured root logger instance.
    """
    # ------------------------------------------------------------------ #
    # 1. Formatter
    # ------------------------------------------------------------------ #
    if json_logs:
        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(request_id)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(request_id)-16s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # ------------------------------------------------------------------ #
    # 2. Root logger + clean slate
    # ------------------------------------------------------------------ #
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in list(root_logger.handlers):  # copy list to avoid skipping
        root_logger.removeHandler(handler)

    # ------------------------------------------------------------------ #
    # 3. Console handler
    # ------------------------------------------------------------------ #
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ------------------------------------------------------------------ #
    # 4. Request-ID correlation across *all* handlers
    # ------------------------------------------------------------------ #
    request_id_filter = RequestIdFilter()
    root_logger.addFilter(request_id_filter)           # root-level
    console_handler.addFilter(request_id_filter)       # explicit (optional)

    # ------------------------------------------------------------------ #
    # 5. Tame noisy third-party loggers
    # ------------------------------------------------------------------ #
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger

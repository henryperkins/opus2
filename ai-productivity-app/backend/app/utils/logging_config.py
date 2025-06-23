"""Enhanced logging configuration with request ID support."""
import logging
import sys
from pythonjsonlogger import jsonlogger
from app.middleware.correlation_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Add request ID to log records."""

    def filter(self, record):
        record.request_id = get_request_id() or "no-request-id"
        return True


def setup_logging(json_logs: bool = False, log_level: str = "INFO"):
    """Configure application logging with request ID support."""

    # Create custom formatter
    if json_logs:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(request_id)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"}
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(request_id)-16s | "
            "%(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Add request ID filter
    request_id_filter = RequestIdFilter()
    console_handler.addFilter(request_id_filter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger

"""Centralised logging configuration helpers.

This module keeps *all* non-standard logging tweaks in one place so the
main application code remains clean.  At the moment we only down-grade the
noisy third-party libraries (httpx/httpcore/openai) to *INFO* when the
process is **not** in debug mode.
"""

from __future__ import annotations

import logging

from app.config import settings


def configure_library_loggers() -> None:  # noqa: D401
    """Adjust log levels for chatty third-party libraries in production."""

    # Keep full DEBUG traces in development for easier network debugging.
    if settings.debug:
        return

    for lib in ("httpx", "httpcore", "openai"):
        logging.getLogger(lib).setLevel(logging.INFO)

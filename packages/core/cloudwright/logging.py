"""Structured logging configuration for Cloudwright."""

from __future__ import annotations

import logging
import os

import structlog

_configured = False


def configure_logging() -> None:
    """Configure structlog for Cloudwright. Call once at startup."""
    global _configured  # noqa: PLW0603
    if _configured:
        return

    log_format = os.environ.get("CLOUDWRIGHT_LOG_FORMAT", "console")

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a stdlib logger. Compatible with pytest caplog and structlog formatting.

    Uses standard logging.getLogger so caplog captures work in tests.
    When configure_logging() has been called, output is formatted by structlog.
    """
    return logging.getLogger(name)

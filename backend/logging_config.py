"""
Career OS — Structured Logging.

Replaces the bare `logging.basicConfig` in server.py with structured
JSON output in production and human-readable output in development.

Why: plaintext logs are unqueryable in production (Render log tails,
Datadog, Logtail). JSON lets you filter by user_id, feature, latency.

Usage:
    from logging_config import configure_logging
    configure_logging()   # call once at startup, before any loggers are created
"""
from __future__ import annotations
import json
import logging
import os
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line — queryable by any log aggregator."""

    _SERVICE = "career-os-backend"
    _VERSION = "2.1.0"
    _ENV     = os.environ.get("ENVIRONMENT", "development")

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict = {
            "ts":      datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
            "service": self._SERVICE,
            "version": self._VERSION,
            "env":     self._ENV,
        }

        # Include exception traceback when present
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        # Merge any extra fields passed via logger.info("msg", extra={...})
        SKIP = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, val in record.__dict__.items():
            if key not in SKIP and not key.startswith("_"):
                payload[key] = val

        return json.dumps(payload, default=str)


class _DevFormatter(logging.Formatter):
    """Coloured, human-readable format for local development."""

    COLOURS = {
        "DEBUG":    "\033[36m",    # cyan
        "INFO":     "\033[32m",    # green
        "WARNING":  "\033[33m",    # yellow
        "ERROR":    "\033[31m",    # red
        "CRITICAL": "\033[35m",    # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        colour = self.COLOURS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S")
        base = f"{colour}{ts} [{record.levelname:8}] {record.name}: {record.getMessage()}{self.RESET}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging(level: str | None = None) -> None:
    """
    Call once at application startup (before any `logging.getLogger` calls).

    - ENVIRONMENT=production  → JSON formatter on stdout
    - ENVIRONMENT=development → coloured dev formatter on stdout
    """
    env       = os.environ.get("ENVIRONMENT", "development")
    log_level = level or os.environ.get("LOG_LEVEL", "INFO")

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove any handlers already attached (e.g. from basicConfig)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _JSONFormatter() if env == "production" else _DevFormatter()
    )
    root.addHandler(handler)

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "motor", "pymongo", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"env": env, "level": log_level, "format": "json" if env == "production" else "dev"},
    )

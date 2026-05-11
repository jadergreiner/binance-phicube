"""
Logger estruturado usando structlog.

Produz logs em JSON (produção) ou formato colorido legível (desenvolvimento).
Todos os módulos devem obter seu logger via get_logger(__name__).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog


def configure_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """Configure structlog and stdlib logging. Call once at startup.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, etc.)
        log_file: Optional file path for JSON log output (e.g. "logs/bot.log").
                  Used in Docker/simulation mode so soak orchestrator can read logs.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    is_tty = sys.stderr.isatty()

    if is_tty:
        # Human-friendly colored output for development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # JSON output for production / log aggregation
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ],
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Always log to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    # Optional file logging (JSON) for soak orchestrator / Docker
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        json_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                *shared_processors,
                structlog.processors.JSONRenderer(),
            ],
        )
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

    root_logger.setLevel(level)

    # Suppress noisy third-party loggers
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    # pymongo 4.x usa LogMessage em threads internas onde logger=None,
    # causando AttributeError no processor add_logger_name do structlog
    logging.getLogger("pymongo").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

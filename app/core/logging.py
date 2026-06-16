import io
import os
import sys
from typing import Any

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    logger.remove()
    logger.configure(extra={"env": settings.APP_ENV})

    if settings.LOG_FORMAT == "json":
        # serialize=True emits one JSON object per line with all record fields
        # (time, level, message, module, function, line, extra, exception).
        # Compatible with ELK, CloudWatch, Datadog, Loki out of the box.
        # enqueue=True makes writes non-blocking — safe in async and threaded code.
        # NOTE: do NOT combine serialize=True with a custom format string —
        #       Loguru ignores format when serialize is active.
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            colorize=False,
            serialize=True,
            enqueue=True,
        )
    else:
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stdout,
            format=fmt,
            level=settings.LOG_LEVEL,
            colorize=True,
        )

    if settings.is_production:
        os.makedirs("logs", exist_ok=True)
        logger.add(
            "logs/finance_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            compression="gz",
            level="INFO",
            serialize=True,
            enqueue=True,
        )


def get_logger(name: str) -> Any:
    return logger.bind(module=name)

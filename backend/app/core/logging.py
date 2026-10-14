import logging
import logging.config
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configures centralized logging for the application."""
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                "datefmt": "%Y-%m-%dT%H:%M:%SZ",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default" if settings.ENVIRONMENT == "development" else "json",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(logging_config)


logger = logging.getLogger("xbike.mrp")

import logging
import logging.config
import os
from typing import TYPE_CHECKING, cast

import structlog
from ddtrace.trace import tracer

if TYPE_CHECKING:
    from structlog.types import Processor


def add_organization_name(logger, method_name, event_dict):
    current_root_span = tracer.current_root_span()
    if current_root_span:
        tags = current_root_span.get_tags()
        if "organization" in tags:
            event_dict["organization"] = tags.get("organization")
        if "dd-organization" in tags:
            event_dict["dd-organization"] = tags.get("dd-organization")

    return event_dict


def get_logging_config(debug: bool | None = None):
    if debug is None:
        debug = not os.getenv("RENDER")

    """
    Lifted from https://github.com/dagster-io/internal/blob/master/dagster-cloud/packages/dagster-cloud-backend/dagster_cloud_backend/loggers/__init__.py#L11
    Much inspiration is taken from https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        add_organization_name,
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

    logging_config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "foreign_pre_chain": shared_processors,
                "processors": [
                    structlog.processors.format_exc_info,
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "foreign_pre_chain": shared_processors,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(
                        exception_formatter=structlog.dev.plain_traceback
                    ),
                ],
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
            "development": {
                "class": "logging.StreamHandler",
                "formatter": "colored",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": True,
            },
            "snowflake.connector.connection": {
                "level": "WARNING",
            },
            "httpx": {
                "level": "WARNING",
            },
            "httpcore": {
                "level": "WARNING",
            },
            "stripe": {
                "level": "WARNING",
            },
            "databricks.sql": {
                "level": "WARNING",
            },
        },
    }

    if debug:
        loggers = cast("dict[str, dict[str, object]]", logging_config["loggers"])
        for logger in loggers:
            loggers[logger].update(
                {
                    "handlers": ["development"],
                }
            )

        # Configure uvicorn.access to have same format
        loggers["uvicorn.access"] = {
            "handlers": ["development"],
            "propagate": False,
        }

    return logging_config


def configure_loggers(debug: bool | None = None):
    import ddtrace.auto  # noqa # pyright: ignore

    logging_config = get_logging_config(debug)
    logging.config.dictConfig(logging_config)

    # If warning exceptions are emitted by external libraries, ensure that they are handled through
    # the logging infrastructure
    logging.captureWarnings(True)

    return logging_config

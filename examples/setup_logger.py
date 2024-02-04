import os
import sys
import logging
import logging.config
import structlog
from structlog.typing import EventDict

CONSOLE_HANDLER: str = "console"
CONSOLE_FORMATTER: str = "console_formatter"

JSONFORMAT_HANDLER: str = "jsonformat"
JSONFORMAT_FORMATTER: str = "jsonformat_formatter"


class SetupLogger:
    def __init__(self) -> None:
        self.web_url = "http://127.0.0.1:3325/addlog"

    def __str__(self) -> str:
        return f"<{__class__.__name__} dev:{sys.stderr.isatty()}>"

    def __repr__(self):
        return self.__str__()

    @property
    def renderer(self) -> str:
        if sys.stderr.isatty() or os.environ.get("DEV", True):
            return CONSOLE_HANDLER
        return JSONFORMAT_HANDLER

    @property
    def timestamper(self) -> structlog.processors.TimeStamper:
        return structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")

    def logger_detailed(self, logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
        filename: str = event_dict.pop("filename")
        func_name: str = event_dict.pop("func_name")
        lineno: str = event_dict.pop("lineno")

        event_dict["logger"] = f"{filename}:{func_name}:{lineno}"

        return event_dict

    def preprocessors(self, addit: bool = False) -> list[any]:
        preprocessors: list[any] = [
            self.timestamper,
            structlog.stdlib.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            self.logger_detailed,
        ]
        if addit:
            preprocessors: list[any] = (
                [
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.filter_by_level,
                ]
                + preprocessors
                + [
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
                ]
            )
        return preprocessors

    def init_structlog(self):
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    JSONFORMAT_FORMATTER: {
                        "()": structlog.stdlib.ProcessorFormatter,
                        "processor": structlog.processors.JSONRenderer(),
                        "foreign_pre_chain": self.preprocessors(),
                    },
                    CONSOLE_FORMATTER: {
                        "()": structlog.stdlib.ProcessorFormatter,
                        "processor": structlog.dev.ConsoleRenderer(),
                        "foreign_pre_chain": self.preprocessors(),
                    },
                },
                "handlers": {
                    CONSOLE_HANDLER: {
                        "class": "logging.StreamHandler",
                        "formatter": CONSOLE_FORMATTER,
                    },
                    JSONFORMAT_HANDLER: {
                        "class": "logging.StreamHandler",
                        "formatter": JSONFORMAT_FORMATTER,
                    },
                },
                "loggers": {
                    "": {
                        "handlers": [self.renderer],
                        "level": "DEBUG",
                        "propagate": True,
                    },
                },
            }
        )

        structlog.configure(
            processors=self.preprocessors(True),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


sl = SetupLogger()
sl.init_structlog()

import logging
from core.middleware.correlation import get_correlation_id


class StructuredLogger:
    """
    Wrapper around Python logging that automatically attaches
    correlation IDs and structured context to every log entry.
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _enrich(self, extra: dict) -> dict:
        correlation_id = get_correlation_id()
        if correlation_id:
            extra["correlation_id"] = correlation_id
        return extra

    def info(self, msg: str, **kwargs):
        self._logger.info(msg, extra=self._enrich(kwargs))

    def warning(self, msg: str, **kwargs):
        self._logger.warning(msg, extra=self._enrich(kwargs))

    def error(self, msg: str, **kwargs):
        self._logger.error(msg, extra=self._enrich(kwargs))

    def debug(self, msg: str, **kwargs):
        self._logger.debug(msg, extra=self._enrich(kwargs))

    def exception(self, msg: str, **kwargs):
        self._logger.exception(msg, extra=self._enrich(kwargs))


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)

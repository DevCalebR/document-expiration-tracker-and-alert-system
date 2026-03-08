import logging
from contextvars import ContextVar
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
except Exception:
    jsonlogger = None

from config import settings

request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
if not hasattr(logging, "_docexpire_original_record_factory"):
    logging._docexpire_original_record_factory = logging.getLogRecordFactory()
_DEFAULT_RECORD_FACTORY = logging._docexpire_original_record_factory
_LOGGING_CONFIGURED = False


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get() or "-"
        return True


def _record_factory(*args, **kwargs):
    record = _DEFAULT_RECORD_FACTORY(*args, **kwargs)
    if not hasattr(record, "request_id") or not record.request_id:
        record.request_id = request_id_ctx_var.get() or "-"
    return record


def setup_logging() -> None:
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return

    logging.setLogRecordFactory(_record_factory)

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    if settings.LOG_FORMAT == "json" and jsonlogger:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s [request_id=%(request_id)s]"
        )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.LOG_LEVEL)
    _LOGGING_CONFIGURED = True

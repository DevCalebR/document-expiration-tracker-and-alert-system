from typing import Any, Dict, Optional
import logging

from config import settings

logger = logging.getLogger(__name__)
_REDIS_CONNECTION = None


def _require(module_name: str):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as exc:
        raise RuntimeError(
            f"Missing optional dependency '{module_name}'. "
            "Install backend requirements to enable queue features."
        ) from exc


def get_redis_connection():
    global _REDIS_CONNECTION
    if _REDIS_CONNECTION is not None:
        return _REDIS_CONNECTION

    if settings.REDIS_URL.startswith("fakeredis://"):
        fakeredis = _require("fakeredis")
        _REDIS_CONNECTION = fakeredis.FakeRedis()
        return _REDIS_CONNECTION

    redis = _require("redis")
    _REDIS_CONNECTION = redis.Redis.from_url(settings.REDIS_URL)
    return _REDIS_CONNECTION


def get_queue():
    rq = _require("rq")
    return rq.Queue(
        name=settings.RQ_QUEUE_NAME,
        connection=get_redis_connection(),
        default_timeout=settings.RQ_JOB_TIMEOUT,
        is_async=settings.RQ_ASYNC,
    )


def get_queue_mode() -> str:
    return "async" if settings.RQ_ASYNC else "eager"


def enqueue_job(func, *args, **kwargs):
    queue = get_queue()
    job = queue.enqueue(func, *args, **kwargs, result_ttl=settings.RQ_RESULT_TTL)
    logger.info("job_enqueued", extra={"job_id": job.id, "job_func": func.__name__})
    return job


def fetch_job(job_id: str):
    try:
        rq_job = _require("rq").job.Job
        return rq_job.fetch(job_id, connection=get_redis_connection())
    except Exception:
        return None

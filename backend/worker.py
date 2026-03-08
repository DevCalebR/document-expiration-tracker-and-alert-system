import logging

from config import settings
from rq import Worker

from logging_config import setup_logging
from job_queue import get_queue, get_redis_connection


def main():
    setup_logging()
    logging.getLogger(__name__).info("worker_starting")
    if not settings.RQ_ASYNC:
        logging.getLogger(__name__).info("worker_not_required_in_eager_mode")
        return
    queue = get_queue()
    worker = Worker([queue], connection=get_redis_connection())
    worker.work()


if __name__ == "__main__":
    main()

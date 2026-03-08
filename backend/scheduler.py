import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler

from config import settings
from jobs import send_expiration_alerts_job
from logging_config import setup_logging
from job_queue import enqueue_job


logger = logging.getLogger(__name__)


def enqueue_alerts():
    if not settings.ALERTS_ENABLED:
        logger.info("alerts_disabled")
        return
    enqueue_job(send_expiration_alerts_job)


def main():
    setup_logging()
    logger.info("scheduler_starting")
    scheduler = BlockingScheduler()
    scheduler.add_job(
        enqueue_alerts,
        trigger="interval",
        hours=settings.ALERT_INTERVAL_HOURS,
        next_run_time=datetime.utcnow() + timedelta(seconds=15),
        id="expiration_alerts",
        replace_existing=True,
    )
    scheduler.start()


if __name__ == "__main__":
    main()

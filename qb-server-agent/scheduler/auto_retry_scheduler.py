import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.qbxml_service import auto_retry_failed_transactions

logger = logging.getLogger("qb_server_agent")


def start_auto_retry_scheduler(app):
    auto_retry_enabled = os.getenv("AUTO_RETRY_ENABLED", "false").lower() == "true"

    if auto_retry_enabled:
        auto_retry_interval_in_seconds = int(os.getenv("AUTO_RETRY_INTERVAL_IN_SECONDS", 60))
        scheduler = BackgroundScheduler()

        def scheduled_task():
            with app.app_context():
                auto_retry_failed_transactions(app)

        scheduler.add_job(
            func=scheduled_task,
            trigger=IntervalTrigger(seconds=auto_retry_interval_in_seconds),
            id="auto_retry_scheduler_task",
            name="Retry failed messages",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Auto retry scheduler started.")

        import atexit
        atexit.register(lambda: scheduler.shutdown())

    else:
        logger.info("Failed messages retry disabled.")

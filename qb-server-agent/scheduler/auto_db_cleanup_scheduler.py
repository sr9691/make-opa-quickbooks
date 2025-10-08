import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.transaction_service import cleanup_old_transactions

logger = logging.getLogger("qb_server_agent")

def start_db_cleanup_scheduler(app):
    auto_retry_enabled = os.getenv("AUTO_DB_CLEANUP", "false").lower() == "true"

    if auto_retry_enabled:
        auto_retry_interval_in_hours = int(os.getenv("AUTO_DB_CLEANUP_INTERVAL_IN_HOURS", 24))

        scheduler = BackgroundScheduler()

        def scheduled_task():
            with app.app_context():
                cleanup_old_transactions()

        scheduler.add_job(
            func=scheduled_task,
            trigger=IntervalTrigger(hours=auto_retry_interval_in_hours),
            id="auto_db_cleanup_task",
            name="Automatic database cleanup",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("DB cleanup scheduler started.")

        import atexit
        atexit.register(lambda: scheduler.shutdown())
    else:
        logger.info("Automatic DB cleanup disabled.")

import os
from datetime import datetime, timezone, UTC, timedelta
from models.transaction import Transaction
from extensions import db
import logging

logger = logging.getLogger("qb_server_agent")

def cleanup_old_transactions():
    logger.info("Starting DB auto cleanup routine")

    retention_days = int(os.getenv("DATABASE_RETENTION_DAYS", 30))
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    with db.session.begin():
        deleted_count = (
            db.session.query(Transaction)
            .filter(Transaction.timestamp < cutoff_date)
            .delete(synchronize_session=False)
        )
        logger.info(f"Deleted {deleted_count} transactions older than {cutoff_date}")
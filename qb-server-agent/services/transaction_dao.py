# services/transaction_service.py
import logging
from datetime import datetime, timezone, UTC

from models.transaction import Transaction
from utils.db_session import db_session_scope

logger = logging.getLogger("qb_server_agent")

def create_transaction(tx: Transaction):
    with db_session_scope() as session:
        session.add(tx)
        session.flush()
        transaction_id = tx.transaction_id

    return transaction_id

def get_transaction_by_id(transaction_id):
    return Transaction.query.get(transaction_id)

def get_transaction_by_idempotency_key(idempotency_key):
    return Transaction.query.filter_by(idempotency_key=idempotency_key).first()

from datetime import datetime

def list_transactions(statuses=None, max_retry_count=None, limit=100, offset=0, since=None):
    query = Transaction.query

    if statuses:
        query = query.filter(Transaction.status.in_(statuses))

    if max_retry_count is not None:
        query = query.filter(Transaction.retry_count <= max_retry_count)

    if since:
        query = query.filter(Transaction.timestamp >= since)

    total = query.count()

    query = query.order_by(Transaction.timestamp.desc())

    if limit is None:
        limit = 100
    elif limit > 1000:
        limit = 1000

    query = query.limit(limit)

    if offset:
        query = query.offset(offset)

    transactions = query.all()

    return transactions, total

def update_transaction(transaction_id, data):
    with db_session_scope() as session:
        tx = session.get(Transaction, transaction_id)
        if not tx:
            return None

        for field in [
            'identifier', 'idempotency_key', 'timestamp', 'status',
            'processing_time_ms', 'qbxml_request', 'qbxml_response',
            'error_message', 'error_code', 'retry_count'
        ]:
            if field in data:
                value = data[field]
                if field == 'timestamp' and value:
                    value = _parse_timestamp(value)
                setattr(tx, field, value)

        tx.updated_at = datetime.now()
        session.flush()
        session.commit()
        return tx

def delete_transaction(transaction_id):
    with db_session_scope() as session:
        tx = session.get(Transaction, transaction_id)
        if not tx:
            return None

        session.delete(tx)
    return True

def _parse_timestamp(value):
    if not value:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(UTC)
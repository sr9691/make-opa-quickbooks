import logging
import os
import time
import uuid
from datetime import datetime, timezone

import requests

from clients.qb_shim_client import request_qbxml
from models.transaction import Transaction
from services.transaction_dao import create_transaction, get_transaction_by_idempotency_key, update_transaction, \
    get_transaction_by_id, list_transactions

logger = logging.getLogger("qb_server_agent")

def process_qbxml_request(qbxml: str, identifier:str, idempotency_key: str) -> dict:
    logger.debug(f'Request received: \nQBXML: {qbxml}\nidentifier: {identifier}\nidempotency_key: {idempotency_key}')
    logger.info(f'Request received for idepotency key: {idempotency_key}')

    resolved_transaction = _resolve_transaction_object(
        idempotency_key=idempotency_key,
        identifier=identifier,
        qbxml=qbxml
    )

    if not resolved_transaction['proceed']:
        conflict = True
        tx_response = {
            'success': True if resolved_transaction['transaction'].status == 'success' else False,
            'identifier': resolved_transaction['transaction'].identifier,
            'qb_response': resolved_transaction['transaction'].qbxml_response,
            'processing_time_ms': resolved_transaction['transaction'].processing_time_ms,
            'trasaction_id': resolved_transaction['transaction'].transaction_id,
            'message': 'Transaction completed successfully' if resolved_transaction['transaction'].status == 'success' else 'in progress'
        }
        return {
            'conflict': conflict,
            'response': tx_response
        }

    tx: Transaction = resolved_transaction['transaction']
    is_retry = resolved_transaction['is_retry']

    return _process_transaction(transaction=tx, is_retry=is_retry)

def retry_transaction_by_id(transaction_id):
    tx = get_transaction_by_id(transaction_id)

    if not tx:
        return None

    elif tx.status == 'success' or tx.status == 'pending':
        tx_response = {
            'success': True if tx.status == 'success' else False,
            'identifier': tx.identifier,
            'qb_response': tx.qbxml_response,
            'processing_time_ms': tx.processing_time_ms,
            'trasaction_id': tx.transaction_id,
            'message': 'Transaction completed successfully' if tx.status == 'success' else 'in progress'
        }
        return {
            'conflict': True,
            'response': tx_response
        }

    else:
        return _process_transaction(transaction=tx, is_retry=True)

def auto_retry_failed_transactions(app):
    max_attempts = os.getenv("AUTO_RETRY_MAX_ATTEMPTS", 3)
    statuses = ['error']

    retriable_transactions = list_transactions(
        max_retry_count=max_attempts,
        statuses=statuses
    )

    if len(retriable_transactions) > 0:
        logger.info(f"Auto retry failed tasks task started at {datetime.now()}. {len(retriable_transactions)} transactions found to retry")
        with app.app_context():
            for detached_tx in retriable_transactions:
                tx = get_transaction_by_id(detached_tx.transaction_id)
                if tx:
                    _process_transaction(transaction=tx, is_retry=True)

def _process_transaction(transaction: Transaction, is_retry: bool) -> dict:
    logger.debug(f"Processing transaction id: {transaction.transaction_id} / idempotency key: {transaction.idempotency_key}")
    tx_id = transaction.transaction_id

    start_time = time.time()
    retries = transaction.retry_count

    try:
        qb_response = request_qbxml(transaction.qbxml_request, transaction.identifier).json()
        processed_time = transaction.processing_time_ms if transaction.processing_time_ms else (time.time() - start_time) * 1000
        logger.debug(f"Response from qb-shim: {qb_response}")

        if qb_response['success']:
            logger.debug(f"Processing succesful response from qb-shim")

            identifier = transaction.identifier
            transaction_id = transaction.transaction_id

            transaction.status = 'success'
            transaction.qbxml_response = qb_response['qbxml_response']
            transaction.processing_time_ms = processed_time
            update_transaction(tx_id, transaction.to_dict())

            response = {
                "success": True,
                "identifier": identifier,
                "qb_response": qb_response['qbxml_response'],
                "processing_time_ms": processed_time,
                "trasaction_id": transaction_id,
                "message": "Transaction completed successfully",
            }
        else:
            transaction.status = 'error'
            transaction.qbxml_response = qb_response['qbxml_response']
            transaction.error_message = qb_response['qb_error_message']
            transaction.error_code = qb_response['error_code']
            transaction.retry_count = retries + 1 if is_retry else retries
            transaction.processing_time_ms = processed_time

            update_transaction(tx_id, transaction.to_dict())

            qb_response['transaction_id'] = tx_id
            response = qb_response

        return {
            'conflict': False,
            'response': response
        }

    except Exception as e:
        logger.error(e)
        error_code = (
            'SHIM_UNAVAILABLE'
            if isinstance(e, (ConnectionError, requests.ConnectionError))
            else 'INTERNAL_ERROR'
        )

        transaction.status = 'error'
        transaction.error_message = str(e)
        transaction.error_code = error_code
        transaction.retry_count = retries + 1 if is_retry else retries
        transaction.processing_time_ms = time.time() - start_time

        update_transaction(tx_id, transaction.to_dict())

        response = {
            "success": False,
            "error": "QuickBooks computer not reachable",
            "error_code": error_code,
            "retry_after_seconds": 60,
            "transaction_id": tx_id
        }

        return {
            'conflict': False,
            'response': response
        }

def _resolve_transaction_object(idempotency_key, identifier, qbxml) -> dict:
    # Cases where the transaction has already been processed and are not eligible for retry
    tx = {}
    if idempotency_key:
        tx = _verify_eligible_for_retry(idempotency_key)

    if 'transaction' not in tx:
        retry_count = 0
        transaction_id = str(uuid.uuid4())
        now = datetime.now()
        new_tx = Transaction(
            transaction_id=transaction_id,
            identifier=identifier,
            idempotency_key=idempotency_key,
            timestamp=now,
            status='pending',
            qbxml_request=qbxml,
            retry_count=retry_count,
            created_at=now,
        )
        tx_id = create_transaction(new_tx)
        tx['transaction'] = get_transaction_by_id(tx_id)
        tx['is_retry'] = False

    elif tx['proceed']:
        tx_id = tx['transaction'].transaction_id
        tx['transaction'].status = 'pending'
        update_transaction(tx['transaction'].transaction_id, tx['transaction'].to_dict())
        tx['transaction'] = get_transaction_by_id(tx_id)

        tx['is_retry'] = True

    return tx

def _verify_eligible_for_retry(idempotency_key) -> dict:
    response = {}

    tx = get_transaction_by_idempotency_key(idempotency_key)
    if tx is not None:
        response['transaction'] = tx
        if tx.status == 'success' or tx.status == 'pending':
            response['proceed'] = False
        else:
            response['proceed'] = True
    else:
        response['proceed'] = True

    return response
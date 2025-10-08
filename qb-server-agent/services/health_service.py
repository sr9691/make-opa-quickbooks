import logging
import os
from datetime import datetime, time

from clients.qb_shim_client import check_qb_shim_health
from services.transaction_dao import list_transactions


logger = logging.getLogger("qb_server_agent")

def check_app_health():
    db_connected, total_tx_today, last_tx = _check_db_connection_and_todays_transactions()
    is_qb_shim_reachable, qb_shim_response, status_code = _check_qb_shim_health()

    status = 'healthy' if db_connected else 'unhealthy'
    timestamp = datetime.now().isoformat()

    response = {
        'status': status,
        'timestamp': timestamp,
        'server_agent': {
            'status': 'running',
            'database': 'connected' if db_connected else 'not connected'
        },
        'qb_shim': {
            'url': os.getenv("QB_SHIM_URL"),
        },
        'quickbooks': { },
        "transactions_today": total_tx_today if db_connected else None,
        "last_transaction": last_tx if db_connected else None
    }

    if is_qb_shim_reachable:
        response['qb_shim']['status'] = 'reachable'
        if 'quickbooks_connected' in qb_shim_response and qb_shim_response['quickbooks_connected']:
            response['quickbooks'] = {
                'status': 'connected',
                'company_file': qb_shim_response['company_file'] if 'company_file' in qb_shim_response else None,
                'company_file_open': qb_shim_response['company_file_open'] if 'company_file_open' in qb_shim_response else None,
                'error': qb_shim_response['error'] if 'error' in qb_shim_response else None
            }

        else:
            response['quickbooks'] = { 'status': 'not connected' }

    else:
        response['qb_shim']['status'] = 'unreachable'
        response['qb_shim']['error'] = qb_shim_response['error'] if 'error' in qb_shim_response else None
        response['quickbooks']['status'] = 'unknown'

    return response

def _check_db_connection_and_todays_transactions():
    try:
        today_start = datetime.combine(datetime.now().date(), time.min)
        transactions, total = list_transactions(since=today_start)

        last_transaction_timestamp = transactions[0].updated_at.isoformat() + "Z" if len(transactions) > 0 else None

        return True, total, last_transaction_timestamp

    except Exception as e:
        logger.error(e)
        return False, None, None

def _check_qb_shim_health():
    try:
        health_check = check_qb_shim_health()
        return True, health_check.json(), health_check.status_code
    except Exception as e:
        return False, {'error': str(e) }, None

from flask import Blueprint, request, jsonify
from datetime import datetime

from models.transaction import Transaction
from services.qbxml_service import retry_transaction_by_id
from services.transaction_dao import get_transaction_by_id, list_transactions

transaction_bp = Blueprint('transaction', __name__)

def validate_limit(limit):
    if limit is None or limit == '':
        return 1000

    if limit > 1000:
        raise ValueError('Limit cannot be greater than 1000')

    return limit

def validate_status(statuses):
    if statuses:
        allowed_statuses = {'success', 'error', 'duplicate', 'pending'}
        for status in statuses:
            if status not in allowed_statuses:
                raise ValueError('Invalid status')

    return statuses

def validate_date(date):
    since_dt = None
    if date:
        since_dt = datetime.fromisoformat(date)

    return since_dt


@transaction_bp.route('/transactions', methods=['GET'])
def get_transactions():
    # Query parameters
    limit = validate_limit(request.args.get('limit', default=100, type=int))
    statuses = validate_status(request.args.getlist('status'))
    since = validate_date(request.args.get('since', default=None, type=str))
    offset = request.args.get('offset', default=0, type=int)

    transactions, total = list_transactions(
        statuses=statuses,
        limit=limit,
        offset=offset,
        since=since
    )

    transactions_data = [
        {
            "transaction_id": t.transaction_id,
            "identifier": t.identifier,
            "idempotency_key": t.idempotency_key,
            "timestamp": t.timestamp.isoformat() + "Z",
            "status": t.status,
            "processing_time_ms": t.processing_time_ms,
            "qbxml_request_size": len(t.qbxml_request) if t.qbxml_request else 0,
            "qbxml_response_size": len(t.qbxml_response) if t.qbxml_response else 0
        }
        for t in transactions
    ]

    response = {
        "transactions": transactions_data,
        "total": total,
        "limit": limit,
        "offset": offset
    }

    return jsonify(response)

@transaction_bp.route('/transactions/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    tx: Transaction = get_transaction_by_id(transaction_id)
    if tx:
        return jsonify(tx.to_dict()), 200
    else:
        return jsonify({'error': 'Transaction not found'}), 404

@transaction_bp.route('/transactions/<transaction_id>/retry', methods=['POST'])
def post_transaction_retry(transaction_id):
    result = retry_transaction_by_id(transaction_id)

    if not result:
        return jsonify({'error': 'Transaction not found'}), 404

    if 'conflict' in result and result['conflict']:
        return jsonify(result['response']), 409

    if 'error_code' in result['response']:
        if result['response']['error_code'] == 'SHIM_UNAVAILABLE':
            return jsonify(result['response']), 503
        else:
            return jsonify(result['response']), 500

    return jsonify(result['response']), 200
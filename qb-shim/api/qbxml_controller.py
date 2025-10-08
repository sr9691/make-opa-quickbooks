import os

from flask import Blueprint, request, jsonify
from services.qbxml_service import QBXMLService

qbxml_bp = Blueprint('qbxml', __name__)
qbxml_service = QBXMLService()


@qbxml_bp.route('/qbxml', methods=['POST'])
def process_qbxml():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required',
                'error_code': 'INVALID_REQUEST'
            }), 400

        qbxml = data.get('qbxml')
        transaction_id = data.get('transaction_id')

        if not qbxml:
            return jsonify({
                'success': False,
                'error': 'qbxml field is required',
                'error_code': 'MISSING_FIELD'
            }), 400

        if not _is_qbxml_size_valid(qbxml):
            return jsonify({
                'success': False,
                'error': 'QBXML size exceeds maximum allowed',
                'error_code': 'INVALID_XML'
            }), 400

        # Call service to process QBXML
        result = qbxml_service.process_qbxml(qbxml, transaction_id)

        if result['success']:
            return jsonify(result), 200
        else:
            if result['error_code'] == 'QB_UNAVAILABLE':
                return jsonify(result), 503
            else:
                return jsonify(result), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'INTERNAL_ERROR'
        }), 500

def _is_qbxml_size_valid(qbxml: str) -> bool:
    if qbxml is None:
        return False

    max_size_mb = float(os.getenv("MAX_QBXML_SIZE_MB", 10))

    size_mb = len(qbxml.encode("utf-8")) / (1024 * 1024)

    return size_mb <= max_size_mb
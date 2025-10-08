from flask import Blueprint, request, jsonify
from services.qbxml_service import process_qbxml_request

qbxml_bp = Blueprint('qbxml', __name__)

@qbxml_bp.route('/qbxml', methods=['POST'])
def post_qbxml():
    content_type = request.headers.get('Content-Type', '').lower().strip()

    if content_type.startswith('application/json'):
        try:
            payload = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "Invalid JSON body"}), 400

        result = _process_json_request(payload)
        return _build_response(result)

    elif content_type.startswith('application/xml') or content_type.startswith('text/xml'):
        raw_xml = request.data.decode('utf-8') if request.data else ''
        if not raw_xml.strip():
            return jsonify({"error": "Empty XML body"}), 400

        request_id = request.headers.get('X-Request-ID')
        idempotency_key = request.headers.get('X-Idempotency-Key')

        result = _process_xml_request(
            body=raw_xml,
            request_id=request_id,
            idempotency_key=idempotency_key
        )
        return _build_response(result)

    else:
        return jsonify({"error": "Unsupported Content-Type"}), 415  # 415 = Unsupported Media Type

def _process_json_request(payload: dict) -> dict:
    return process_qbxml_request(
        qbxml=payload['qbxml'],
        identifier=payload['identifier'],
        idempotency_key=payload['idempotency_key']
    )

def _process_xml_request(body: str, request_id: str = None, idempotency_key: str = None) -> dict:
    return process_qbxml_request(
        qbxml=body,
        identifier=request_id,
        idempotency_key=idempotency_key
    )

def _build_response(result: dict):
    response_data = result.get('response', {})

    if result.get('conflict'):
        return jsonify(response_data), 409

    if response_data.get('error_code') == 'SHIM_UNAVAILABLE':
        return jsonify(response_data), 503

    if response_data.get('error_code'):
        return jsonify(response_data), 500

    return jsonify(response_data), 200
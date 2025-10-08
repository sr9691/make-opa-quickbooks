from flask import Blueprint, jsonify
from services.health_service import HealthService

health_bp = Blueprint('health', __name__)
health_service = HealthService()


@health_bp.route('/health', methods=['GET'])
def check_health():
    try:
        health_status = health_service.get_health_status()
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503
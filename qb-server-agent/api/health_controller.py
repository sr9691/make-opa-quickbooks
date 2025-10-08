from flask import Blueprint, request, jsonify
from services.health_service import check_app_health

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def check_health():
    return jsonify(check_app_health()), 200
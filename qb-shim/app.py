import os
import logging
from flask import Flask, request, abort
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
from api.qbxml_controller import qbxml_bp
from api.health_controller import health_bp
from utils.log_recording_config import configure_logging

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

app = Flask(__name__)

# allowed ips config
allowed_ips = os.getenv("ALLOWED_IPS", "")
allowed_ips = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]

@app.before_request
def restrict_ip_access():
    client_ip = request.remote_addr
    if allowed_ips and client_ip not in allowed_ips:
        app.logger.warning(f"Acesso negado para IP: {client_ip}")
        abort(403, description="Access denied: your IP is not allowed.")

if os.getenv("SHIM_CORS_ENABLE", "false").lower() == "true":
    CORS(app)

# Get API URL prefix from environment variable with default
api_prefix = os.getenv('SHIM_API_URL_PREFIX', '/')

# Register blueprints
app.register_blueprint(qbxml_bp, url_prefix=api_prefix)
app.register_blueprint(health_bp, url_prefix=api_prefix)

def _set_app_logger_level():
    log_level = os.getenv('LOG_LEVEL', 'ERROR').upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # Force reconfiguration of root logger
    )

    # Explicitly set level for all application loggers
    for logger_name in ['services', 'api']:
        logging.getLogger(logger_name).setLevel(getattr(logging, log_level))

_set_app_logger_level()


def main():
    """Função de entrada para rodar o servidor Flask"""
    host = os.getenv('SHIM_HOST', '0.0.0.0')
    port = int(os.getenv('SHIM_PORT', 5000))
    debug = os.getenv('SHIM_FLASK_DEBUG', 'False').lower() == 'true'

    configure_logging()

    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
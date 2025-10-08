import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text

from extensions import db
from api.health_controller import health_bp
from api.transaction_controller import transaction_bp
from api.qbxml_controller import qbxml_bp
from utils.db_startup import start_db_file
from utils.log_recording_config import configure_logging
from scheduler.auto_retry_scheduler import start_auto_retry_scheduler
from scheduler.auto_db_cleanup_scheduler import start_db_cleanup_scheduler

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")

@app.before_request
def verify_api_key():
    # allows health check to pass
    if request.endpoint in ('health_bp.health_check', 'static'):
        return

    provided_key = request.headers.get("X-API-KEY") or request.args.get("api_key")

    if not API_KEY:
        return jsonify(
            {
                "error_code": "INTERNAL_ERROR",
                "error": "Server misconfiguration: API_KEY not set"
            }
        ), 500

    if not provided_key or provided_key != API_KEY:
        return jsonify({"error_code": "UNAUTHORIZED"}), 401

# Database configuration
start_db_file(app)

# Initializes database in app
db.init_app(app)

# Enables CORS if configured
if os.getenv("QB_AGENT_ENABLE_CORS", "false").lower() == "true":
    CORS(app)

# API prefix
api_prefix = os.getenv('QB_AGENT_API_URL_PREFIX', '/')

# Registers blueprints
app.register_blueprint(transaction_bp, url_prefix=api_prefix)
app.register_blueprint(health_bp, url_prefix=api_prefix)
app.register_blueprint(qbxml_bp, url_prefix=api_prefix)

def _set_app_logger_level():
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

    for logger_name in ['services', 'api']:
        logging.getLogger(logger_name).setLevel(getattr(logging, log_level))

_set_app_logger_level()

def init_database():
    schema_path_env = os.getenv("DATABASE_SCHEMA_SCRIPT_PATH")
    if schema_path_env:
        sql_script_path = Path(schema_path_env).expanduser().resolve()
    else:
        base_dir = Path(__file__).parent
        sql_script_path = base_dir / "schema.sql"

    if not sql_script_path.exists():
        print(f"No SQL schema file found at {sql_script_path}, skipping database initialization")
        return

    with app.app_context():
        with open(sql_script_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        with db.engine.connect() as connection:
            for statement in sql_script.split(";"):
                statement = statement.strip()
                if statement:
                    connection.execute(text(statement))
            connection.commit()

        print(f"Database initialized from {sql_script_path}")

def main():
    host = os.getenv('SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('SERVER_PORT', 5000))
    debug = os.getenv('LOG_LEVEL', 'False').lower() == 'true'

    init_database()
    configure_logging()
    start_auto_retry_scheduler(app)
    start_db_cleanup_scheduler(app)

    if debug:
        app.run(host=host, port=port, debug=debug)
    else:
        from waitress import serve
        print(f"Starting Waitress server on {host}:{port}")
        serve(app, host=host, port=port, threads=4)

if __name__ == '__main__':
    main()

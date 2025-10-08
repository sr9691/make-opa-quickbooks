import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

def configure_logging():
    log_dir = os.getenv("LOG_FILE_PATH", "./logs")
    log_filename = os.getenv("LOG_FILE", "qb_shim.log")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json")
    log_file_enabled = os.getenv("LOG_FILE_ENABLED", "false").lower() == "true"

    # Inclui o nome do arquivo no console
    plain_text_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # Formatações específicas para arquivo
    if log_format == "json":
        file_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)d %(message)s",
            json_ensure_ascii=False
        )
    elif log_format == "xml":
        class XMLFormatter(logging.Formatter):
            def format(self, record):
                return (
                    f"<log>"
                    f"<time>{self.formatTime(record)}</time>"
                    f"<level>{record.levelname}</level>"
                    f"<logger>{record.name}</logger>"
                    f"<file>{record.filename}</file>"
                    f"<line>{record.lineno}</line>"
                    f"<message>{record.getMessage()}</message>"
                    f"</log>"
                )
        file_formatter = XMLFormatter()
    else:
        file_formatter = plain_text_formatter

    app_logger = logging.getLogger("qb_shim")
    app_logger.setLevel(getattr(logging, log_level, logging.INFO))
    app_logger.propagate = False

    # Handler para arquivo
    if log_file_enabled:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_path = Path(log_dir) / log_filename

        file_handler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, log_level, logging.INFO))
        app_logger.addHandler(file_handler)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(plain_text_formatter)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    app_logger.addHandler(console_handler)

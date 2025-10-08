import os
import requests
from requests.exceptions import RequestException, Timeout
import logging

logger = logging.getLogger(__name__)

def check_qb_shim_health():
    url = os.getenv("QB_SHIM_URL")
    qb_shim_connect_timeout_seconds = float(os.getenv("QB_SHIM_CONNECT_TIMEOUT_SECONDS", 5))
    qb_shim_timeout_seconds = float(os.getenv("QB_SHIM_TIMEOUT_SECONDS", 30))

    try:
        response = requests.get(
            url=f"{url}/health",
            timeout=(qb_shim_connect_timeout_seconds, qb_shim_timeout_seconds)
        )

        return response

    except Timeout as e:
        logger.error(f"Timeout while connecting to QB Shim for health check")
        raise e

    except RequestException as e:
        logger.error(f"Error checking qb_shim health: {str(e)}")
        raise e

def request_qbxml(qbxml: str, transaction_id: str):
    url = os.getenv("QB_SHIM_URL")
    qb_shim_connect_timeout_seconds = float(os.getenv("QB_SHIM_CONNECT_TIMEOUT_SECONDS", 5))
    qb_shim_timeout_seconds = float(os.getenv("QB_SHIM_TIMEOUT_SECONDS", 30))

    payload = {
        "qbxml": qbxml,
        "transaction_id": transaction_id
    }

    try:
        response = requests.post(
            url=f"{url}/qbxml",
            json=payload,
            headers={ "Content-Type": "application/json" },
            timeout=(qb_shim_connect_timeout_seconds, qb_shim_timeout_seconds)
        )

        try:
            return response
        except ValueError as e:
            logger.error(f"Response from QB Shim is not valid JSON for transaction {transaction_id}")
            raise e

    except Timeout as e:
        logger.error(f"Timeout while connecting to QB Shim for transaction {transaction_id}")
        raise e

    except RequestException as e:
        logger.error(f"RequestException for transaction {transaction_id}: {str(e)}")
        raise e

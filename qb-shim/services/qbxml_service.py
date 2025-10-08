import os
import logging
import re
from datetime import datetime

from services.quickbooks_connector import QuickBooksConnector

logger = logging.getLogger("qb_shim")

class QBXMLService:

    def process_qbxml(self, qbxml: str, transaction_id: str = None) -> dict:
        logger.info(f'Received QBXML request for transaction_id: {transaction_id}')

        start_time = datetime.now()
        qb = QuickBooksConnector()
        opened_connection = False

        response = {}

        try:
            open_mode = int(os.getenv("QB_OPEN_MODE", 1))
            opened_connection = qb.open_connection()
            qb.begin_session(mode=open_mode, company_file_path=os.getenv("QB_COMPANY_FILE", ""))

        except Exception as e:
            logger.error(f"QuickBooks connection failed: {str(e)}")
            response['success'] = False
            response['error'] = 'QuickBooks is not running or company file not open'
            response['error_code'] = 'QB_UNAVAILABLE'

            if opened_connection:
                qb.close_connection()

            return response

        try:
            qbxml_response = qb.send_xml_request(qbxml)
            end_time = datetime.now()
            logger.debug(f'Response from QuickBooks: {qbxml_response}')

            processing_time = int((end_time - start_time).total_seconds() * 1000)

            response['success'] = True
            response['qbxml_response'] = qbxml_response.replace('\n', '')
            response['processing_time_ms'] = processing_time

            logger.debug(f'Response to be returned: {response}')
            return response

        except Exception as e:
            logger.error(f"Quickbooks failed to process QBXML request: {str(e)}")
            response['success'] = False
            response['error'] = 'QuickBooks returned an error'
            response['error_code'] = 'QB_ERROR'
            response['qb_response'] = str(e)

            exc_str = e.args[0] if e.args else ""

            exc_info = self._parse_qb_exception_string(exc_str)
            response['qb_error_code'] = str(exc_info['error_code'])
            response['qb_error_message'] = exc_info['error_message']

            return response

        finally:
            if opened_connection:
                qb.close_connection()

    def _parse_qb_exception_string(self, exc_str: str) -> dict:
        result = {
            "error_code": None,
            "error_message": None
        }

        if not exc_str:
            return result

        try:
            # Extract the last integer inside the outer tuple -> SCODE
            scode_match = re.search(r"\(\s*0,\s*'[^']+',\s*'[^']+',\s*None,\s*0,\s*(-?\d+)\)", exc_str)
            if scode_match:
                result["error_code"] = int(scode_match.group(1))

            qb_msg_match = re.search(r"\(\s*0,\s*'[^']+',\s*'([^']+)'", exc_str)
            if qb_msg_match:
                result["error_message"] = qb_msg_match.group(1)

        except Exception:
            pass

        return result

import os
import logging
import re
import sys
from datetime import datetime

if sys.platform == 'win32':
    try:
        import win32com.client
        import pythoncom  # type: ignore
    except ImportError:
        win32com = None
        pythoncom = None
else:
    # Mock win32com for non-Windows platforms (development purposes)
    win32com = None
    pythoncom = None

logger = logging.getLogger("qb_shim")

class QBXMLService:

    def process_qbxml(self, qbxml: str, transaction_id: str = None) -> dict:
        logger.info(f'Received QBXML request for transaction_id: {transaction_id}')

        start_time = datetime.now()
        request_processor = None
        ticket = None
        response = {}

        try:
            open_mode = int(os.getenv("QB_OPEN_MODE", 2))
            pythoncom.CoInitialize()
            try:
                logger.debug("Trying QBXMLRP2.RequestProcessor2...")
                request_processor = win32com.client.Dispatch("QBXMLRP2.RequestProcessor2")
            except Exception as e:
                logger.warning(f"Failed with RequestProcessor2: {str(e)}. Falling back to RequestProcessor...")
                request_processor = win32com.client.Dispatch("QBXMLRP2.RequestProcessor")

            request_processor.OpenConnection2("", os.getenv("QB_APP_NAME", "QuickBooks Integration Shim"), 1)

            logger.info(f"Beggining session with mode {open_mode}.")
            ticket = request_processor.BeginSession(os.getenv("QB_COMPANY_FILE", ""), mode=open_mode)
            logger.info(f"✓ Successfully began QuickBooks session. Ticket: {self.ticket}")

        except Exception as e:
            logger.error(f"QuickBooks connection failed: {str(e)}")
            response['success'] = False
            response['error'] = 'QuickBooks is not running or company file not open'
            response['error_code'] = 'QB_UNAVAILABLE'

        try:
            qbxml_response = request_processor.ProcessRequest(ticket, qbxml)
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
            if ticket is not None:
                request_processor.EndSession(ticket)
            if request_processor is not None:
                request_processor.CloseConnection()

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

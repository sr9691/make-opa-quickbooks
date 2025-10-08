import os
import logging

from datetime import datetime, timezone
from services.quickbooks_connector import QuickBooksConnector


logger = logging.getLogger("qb_shim")

class HealthService:

    def get_health_status(self) -> dict:
        logger.info("Checking QuickBooks health status")
        qb = QuickBooksConnector()
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        response = {'timestamp': timestamp}
        error = None

        quickbooks_connected = False
        session_started = False

        # Test open connection
        try:
            quickbooks_connected = qb.open_connection()
            response['quickbooks_connected'] = quickbooks_connected

        except Exception as e:
            response['company_file_open'] = False
            error = 'QuickBooks connection test failed'

        # Test begin session
        if quickbooks_connected:
            try:
                open_mode = int(os.getenv("QB_OPEN_MODE", 1))
                qb.begin_session(mode=open_mode, company_file_path=os.getenv("QB_COMPANY_FILE", ""))
                session_started = True
            except Exception as e:
                logger.debug(f"QuickBooks connection is working, but session couldn't be started: {str(e)}")
                response['company_file_open'] = False
                error = 'QuickBooks connection is working, but session couldn\'t be started'

        # Test open company file
        opened_file_path = qb.get_company_file_path() if session_started else None
        if opened_file_path is not None:
            response['company_file'] = opened_file_path
            response['company_file_open'] = True
        else:
            response['company_file_open'] = False
            error = 'QuickBooks connection and session are working, but test query failed' if error is None else error

        if error is not None:
            response['error'] = error

        response['status'] = 'Healthy' if error is None else 'Unhealthy'

        if quickbooks_connected:
            qb.close_connection()

        return response
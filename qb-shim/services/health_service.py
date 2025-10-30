import os
import logging
import sys

from datetime import datetime, timezone

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

class HealthService:

    def get_health_status(self) -> dict:
        logger.info("Checking QuickBooks health status")

        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        response = {'timestamp': timestamp}
        error = None
        request_processor = None

        quickbooks_connected = False
        session_started = False

        quickbooks_connected = False
        try:
            pythoncom.CoInitialize()
            try:
                logger.debug("Trying QBXMLRP2.RequestProcessor2...")
                request_processor = win32com.client.Dispatch("QBXMLRP2.RequestProcessor2")
                request_processor.OpenConnection2("", os.getenv("QB_APP_NAME", "QuickBooks Integration Shim"), 1)
                quickbooks_connected = True
                response['quickbooks_connected'] = quickbooks_connected
            except Exception as e:
                logger.warning(f"Failed with RequestProcessor2: {str(e)}. Falling back to RequestProcessor...")
                request_processor = win32com.client.Dispatch("QBXMLRP2.RequestProcessor")
                request_processor.OpenConnection2("", os.getenv("QB_APP_NAME", "QuickBooks Integration Shim"), 1)
                quickbooks_connected = True
                response['quickbooks_connected'] = quickbooks_connected

        except Exception as e:
            response['company_file_open'] = False
            error = 'QuickBooks connection test failed'

        # Test begin session
        ticket = None
        if quickbooks_connected:
            try:
                open_mode = int(os.getenv("QB_OPEN_MODE", 2))
                ticket = request_processor.BeginSession(os.getenv("QB_COMPANY_FILE", ""), mode=open_mode)
                session_started = True
            except Exception as e:
                logger.debug(f"QuickBooks connection is working, but session couldn't be started: {str(e)}")
                response['company_file_open'] = False
                response['error'] = 'QuickBooks connection is working, but session couldn\'t be started'
                response['status'] = 'Unhealthy'
                return response

        # Test open company file
        if ticket is not None:
            opened_file_path = None

            try:
                qbxml_get_company = """<?xml version="1.0" encoding="utf-8"?>
                                    <?qbxml version="13.0"?>
                                    <QBXML>
                                        <QBXMLMsgsRq onError="stopOnError">
                                            <CompanyQueryRq requestID="1">
                                            </CompanyQueryRq>
                                        </QBXMLMsgsRq>
                                    </QBXML>"""

                qb_response = request_processor.ProcessRequest(ticket, qbxml_get_company)

                opened_file_path = self._parse_company_file_response(qb_response)

                logger.debug(f'Response from QuickBooks: {qb_response}')
            except Exception as e:
                logger.error(f"Failed to retrieve company file info: {str(e)}")

        if opened_file_path is not None:
            response['company_file'] = opened_file_path
            response['company_file_open'] = True
        else:
            response['company_file_open'] = False
            error = 'QuickBooks connection and session are working, but test query failed' if error is None else error

        if error is not None:
            response['error'] = error

        response['status'] = 'Healthy' if error is None else 'Unhealthy'

        if ticket is not None:
            request_processor.EndSession(ticket)

        if request_processor is not None:
            request_processor.CloseConnection()

        return response

    def _parse_company_file_response(self, qb_response):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(qb_response)

        # Extract company information
        company_ret = root.find('.//CompanyRet')

        if company_ret is not None:
            self.company_file_path = company_ret.findtext('CompanyName', '')
            self.company_name = company_ret.findtext('CompanyName', '')

            # Try to get the legal company name as well
            legal_name = company_ret.findtext('LegalCompanyName', self.company_name)

            info = {
                'company_name': self.company_name,
                'legal_company_name': legal_name,
                'is_sample_file': company_ret.findtext('IsSampleCompany', 'false').lower() == 'true',
                'company_type': company_ret.findtext('CompanyType', 'Unknown'),
                'tax_form': company_ret.findtext('TaxForm', 'Unknown'),
                'first_fiscal_year_month': company_ret.findtext('FiscalYearStartMonth', 'Unknown'),
            }

            # Get address if available
            address = company_ret.find('Address')
            if address is not None:
                info['address'] = {
                    'addr1': address.findtext('Addr1', ''),
                    'city': address.findtext('City', ''),
                    'state': address.findtext('State', ''),
                    'postal_code': address.findtext('PostalCode', ''),
                    'country': address.findtext('Country', 'US'),
                }

            logger.info(f"Retrieved company file info: {self.company_name}")
            return info
        else:
            raise Exception("Could not parse company information from QuickBooks response")
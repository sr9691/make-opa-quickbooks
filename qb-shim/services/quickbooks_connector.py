import os
import sys
import logging
from threading import Lock, Thread

# Conditional import for Windows-only win32com module
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


class QuickBooksConnector:
    """
    Singleton connector for QuickBooks Desktop using QBXMLRP2 COM interface.
    Provides methods to manage QuickBooks connection and session lifecycle.

    Based on QuickBooks SDK documentation and COM integration patterns.
    References:
    - https://developer.intuit.com/app/developer/qbdesktop/docs/develop/communicating-with-quickbooks
    - pywin32 COM client for QBXMLRP2
    
    Note: This connector only works on Windows systems with QuickBooks Desktop installed.
    On non-Windows platforms, methods will raise NotImplementedError.
    
    Singleton pattern ensures only one connection instance exists throughout the application.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        Create or return the singleton instance of QuickBooksConnector.
        Thread-safe implementation using double-checked locking.
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super(QuickBooksConnector, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the connector only once"""
        # Prevent re-initialization
        if self._initialized:
            return
        
        self.request_processor = None
        self.ticket = None
        self.is_connected = False
        self.is_session_open = False
        self.company_file_path = None
        self.company_name = None
        self._check_platform()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> 'QuickBooksConnector':
        """
        Get the singleton instance of QuickBooksConnector.

        Returns:
            QuickBooksConnector: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance. Useful for testing.
        Warning: This will lose the current connection state.
        """
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.close_connection()
                except Exception as e:
                    logger.warning(f"Error closing connection during reset: {str(e)}")
            cls._instance = None

    def _check_platform(self):
        """Check if running on Windows platform"""
        if sys.platform != 'win32':
            logger.warning("QuickBooks Desktop integration only works on Windows platform")

    def _ensure_windows(self):
        """Raise error if not on Windows"""
        if sys.platform != 'win32' or win32com is None:
            raise NotImplementedError(
                "QuickBooks Desktop integration is only available on Windows. "
                "Current platform: " + sys.platform
            )

    def open_connection(self):
        """
        Open a connection to QuickBooks Desktop using QBXMLRP2 COM interface.
        Tries RequestProcessor2 first, then falls back to RequestProcessor.

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            NotImplementedError: If not running on Windows
            Exception: If unable to create COM object or connection fails
        """
        self._ensure_windows()

        # If already connected, return True
        if self.is_connected and self.request_processor is not None:
            logger.info("Connection already open")
            return True

        try:
            # Initialize COM for this thread BEFORE creating COM objects
            self._initialize_com()

            try:
                logger.debug("Trying QBXMLRP2.RequestProcessor2...")
                self.request_processor = win32com.client.Dispatch("QBXMLRP2.RequestProcessor2")
            except Exception as e:
                logger.warning(f"Failed with RequestProcessor2: {str(e)}. Falling back to RequestProcessor...")
                try:
                    self.request_processor = win32com.client.Dispatch("QBXMLRP2.RequestProcessor")
                except Exception as e2:
                    logger.error(f"Failed with RequestProcessor as well: {str(e2)}")
                    raise Exception(f"Could not create QuickBooks RequestProcessor: {str(e2)}") from e2

            # Open the connection
            self.request_processor.OpenConnection2("", os.getenv("QB_APP_NAME", "QuickBooks Integration Shim"), 1)
            self.is_connected = True
            logger.info("Successfully opened connection to QuickBooks Desktop")
            return True

        except Exception as e:
            self.is_connected = False
            self.request_processor = None
            logger.error(f"Failed to open QuickBooks connection: {str(e)}")
            raise Exception(f"Could not connect to QuickBooks: {str(e)}")

    def begin_session(self, company_file_path: str = "", mode: int = 0):
        """
        Begin a session with QuickBooks Desktop with a timeout.

        Args:
            company_file_path (str): Path to the QuickBooks company file (.QBW)
            mode (int): Connection mode (0 = do not care, 1 = single-user, 2 = multi-user)

        Returns:
            str: Session ticket for subsequent operations

        Raises:
            Exception: If session cannot be started or if timeout occurs
        """
        self._ensure_windows()

        if not self.is_connected or self.request_processor is None:
            raise Exception("Connection must be opened before beginning a session")

        timeout_sec = int(os.getenv("QB_SESSION_TIMEOUT", "30"))  # default 30s
        result = {}
        exception_holder = {}

        def target():
            try:
                result['ticket'] = self.request_processor.BeginSession(company_file_path, mode)
            except Exception as e:
                exception_holder['error'] = e

        thread = Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout_sec)

        if thread.is_alive():
            # Timeout hit
            logger.error(f"BeginSession timed out after {timeout_sec} seconds")
            # Ensure connection cleanup
            try:
                self.close_connection()
            except Exception as e:
                logger.warning(f"Error during connection cleanup after timeout: {str(e)}")
            raise TimeoutError(f"QuickBooks BeginSession timed out after {timeout_sec} seconds")

        if 'error' in exception_holder:
            self.is_session_open = False
            raise Exception(f"Could not begin session: {exception_holder['error']}")

        # Success
        self.ticket = result['ticket']
        self.is_session_open = True
        logger.info(f"Successfully began QuickBooks session. Ticket: {self.ticket}")
        return self.ticket


    def get_company_file_info(self) -> dict:
        """
        Retrieve information about the currently open QuickBooks company file.

        Returns:
            dict: Company file information including:
                - company_file_path: Full path to the .QBW file
                - company_name: Name of the company
                - is_sample_file: Whether this is a sample company file
                - qb_file_version: QuickBooks file version
                - country: Country code

        Raises:
            Exception: If session not open or query fails
        """
        self._ensure_windows()

        if not self.is_session_open or self.ticket is None:
            raise Exception("Session must be open to retrieve company file info")

        try:
            # Build QBXML request to get company info
            qbxml_request = """<?xml version="1.0" encoding="utf-8"?>
                <?qbxml version="13.0"?>
                <QBXML>
                    <QBXMLMsgsRq onError="stopOnError">
                        <CompanyQueryRq requestID="1">
                        </CompanyQueryRq>
                    </QBXMLMsgsRq>
                </QBXML>"""

            # Send request to QuickBooks
            response = self.send_xml_request(qbxml_request)
            logger.debug(f'Response from QuickBooks: {response}')

            # Parse response (basic parsing - you might want to use xml.etree or lxml)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response)

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

        except Exception as e:
            logger.error(f"Failed to retrieve company file info: {str(e)}")
            raise Exception(f"Could not get company file info: {str(e)}")

    def get_company_file_path(self) -> str:
        """
        Get the path of the currently open company file.
        This retrieves it from cached info or queries QuickBooks if needed.

        Returns:
            str: Path to the company file or company name
        """
        if self.company_file_path is None and self.is_session_open:
            try:
                info = self.get_company_file_info()
                return info.get('company_name', 'Unknown')
            except Exception as e:
                logger.warning(f"Could not retrieve company file path: {str(e)}")
                return 'Unknown'

        return self.company_file_path or 'Not connected'

    def send_xml_request(self, qbxml_request):
        """
        Send QBXML request to QuickBooks and get response.

        Args:
            qbxml_request (str): Valid QBXML request string

        Returns:
            str: QBXML response from QuickBooks

        Raises:
            NotImplementedError: If not running on Windows
            Exception: If session not open or request processing fails
        """
        self._ensure_windows()

        if not self.is_session_open or self.ticket is None:
            raise Exception("Session must be open before sending requests")

        if not qbxml_request or not isinstance(qbxml_request, str):
            raise ValueError("QBXML request must be a non-empty string")

        try:
            # Process the request and get response
            response = self.request_processor.ProcessRequest(self.ticket, qbxml_request)
            logger.debug("Successfully processed QBXML request")
            return response

        except Exception as e:
            logger.error(f"Failed to process QBXML request: {str(e)}")
            raise Exception(f"QBXML request failed: {str(e)}")

    def end_session(self):
        """
        End the current QuickBooks session.

        Returns:
            bool: True if session ended successfully

        Raises:
            NotImplementedError: If not running on Windows
            Exception: If no active session or ending session fails
        """
        self._ensure_windows()

        if not self.is_session_open or self.ticket is None:
            logger.warning("No active session to end")
            return False

        try:
            self.request_processor.EndSession(self.ticket)
            self.is_session_open = False
            self.ticket = None
            logger.info("Successfully ended QuickBooks session")
            return True

        except Exception as e:
            logger.error(f"Failed to end QuickBooks session: {str(e)}")
            raise Exception(f"Could not end session: {str(e)}")

    def close_connection(self):
        """
        Close the connection to QuickBooks Desktop.

        Returns:
            bool: True if connection closed successfully

        Raises:
            NotImplementedError: If not running on Windows
        """
        self._ensure_windows()

        try:
            # End session first if still open
            if self.is_session_open:
                try:
                    self.end_session()
                except Exception as e:
                    logger.warning(f"Error ending session during connection close: {str(e)}")

            # Close the connection
            if self.request_processor is not None:
                try:
                    self.request_processor.CloseConnection()
                    logger.info("Called CloseConnection on QuickBooks")
                except Exception as e:
                    logger.warning(f"Error calling CloseConnection: {str(e)}")

                self.request_processor = None
                self.is_connected = False
                logger.info("Successfully closed QuickBooks connection")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to close QuickBooks connection: {str(e)}")
            self.is_connected = False
            self.request_processor = None
            raise Exception(f"Could not close connection: {str(e)}")

    def __enter__(self):
        """Context manager entry - opens connection"""
        self.open_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed"""
        try:
            self.close_connection()
        except Exception as e:
            logger.error(f"Error during context manager cleanup: {str(e)}")
        return False

    def _initialize_com(self):
        """Initialize COM for the current thread if needed"""
        if sys.platform == 'win32' and pythoncom is not None:
            try:
                # Use CoInitializeEx with COINIT_MULTITHREADED for better Flask support
                pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
                logger.debug("COM initialized for current thread (multithreaded)")
            except Exception as e:
                # If already initialized, try single-threaded
                try:
                    pythoncom.CoInitialize()
                    logger.debug("COM initialized for current thread (single-threaded)")
                except:
                    # Already initialized, which is fine
                    logger.debug(f"COM already initialized: {str(e)}")
# QB Shim - QuickBooks Desktop Integration Service

A Python Flask application that provides a REST API for integrating with QuickBooks Desktop through the QuickBooks SDK.

## Requirements

- Python 3.12.x - **MAKE SURE TO USE 32-BIT PYTHON**
- Windows operating system (for QuickBooks Desktop integration)
- QuickBooks Desktop installed
- pywin32 for COM object access

Also check `.env` containing all the possible environment variables with examples.

## Installation

### From Source

1. Clone the repository:
```bash
git clone <repository-url>
cd qb-shim
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. If you want to run manually:
   
    1. Package the application:
    ```bash
    python -m zipapp . -m "app:main" -o qb-shim.pyz
    ```

   2. Run:
    ```bash
    python .\qb-shim.pyz
    ```
4. If you want to run as service:
```bash
python app_service.py install
```

5. If you want to run as executable:

   1. First you need to install pyinstaller:
   
   ```bash
   python app_service.py install
   ```
   2. Then package it in the executable format:
   ```bash
   pyinstaller --onefile --name qb_shim app.py
   ```
Note that the executable will be available in the dist folder. Also have in mind that the executable will be specific for the operating system that executed the packaging

**IMPORTANT**: Both the `qb-shim.pyz` and `QuickBooks` apps must run under the same privileges (running as administrator is better)

## API Endpoints

### POST /api/qbxml

Process QBXML requests through QuickBooks Desktop.

**Request:**
```json
{
    "qbxml": "<QBXML>...</QBXML>",
    "transaction_id": "tx-abc123"
}
```

**Success Response:**
```json
{
    "success": true,
    "qbxml_response": "<QBXML>...</QBXML>",
    "processing_time_ms": 2450
}
```

**Error Response:**
```json
{
    "success": false,
    "error": "QuickBooks returned an error",
    "error_code": "QB_ERROR",
    "qb_error_message": "Customer not found",
    "qb_error_code": "3100",
    "qb_response": "<QBXML>...</QBXML>"
}
```

### GET /api/health

Check the health status of the service and QuickBooks connection.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-10-01T12:34:56Z",
    "quickbooks_connected": true,
    "company_file": "C:\\QB\\Company.QBW",
    "company_file_open": true
}
```

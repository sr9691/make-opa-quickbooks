# QB Shim - QuickBooks Desktop Integration Service

A Python Flask application that provides a REST API for integrating with QuickBooks Desktop in a different server that exposes it using QB Shim Connector.

## Requirements

- Python 3.12.x
- Windows operating system (for QuickBooks Desktop integration)
- Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/
- SQLite Database script (path should be declared as DATABASE_SCHEMA_SCRIPT_PATH - value example: ./sql/schema.sql)
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
   pyinstaller --onefile --name qb_server_agent app.py
   ```
Note that the executable will be available in the dist folder. Also have in mind that the executable will be specific for the operating system that executed the packaging

6. Using installer script for Windows:
   1. Open PowerShell with administrative privileges
   2. Execute:
   ```bash
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   ./install_qb_shim.ps1
   ```

## API Token

This API requires an API token to be used. It should be set in the environment variable `API_TOKEN`.

As a suggestion, you can generate a random token using the following command:
```python -c "import secrets; print(secrets.token_hex(32))"```



Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
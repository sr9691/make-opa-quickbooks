Write-Host "Stopping and removing QB Shim Service..."
& "C:\Program Files\qb_shim\venv\Scripts\python.exe" "C:\Program Files\qb_shim\app_service.py" stop
& "C:\Program Files\qb_shim\venv\Scripts\python.exe" "C:\Program Files\qb_shim\app_service.py" remove

Write-Host "Removing installation directory..."
Remove-Item -Recurse -Force "C:\Program Files\qb_server_agent"
Write-Host "✅ QB Shim Service uninstalled successfully."
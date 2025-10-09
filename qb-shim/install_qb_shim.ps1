<#
.SYNOPSIS
    Installation script for QB Shim Service (Windows only)

.DESCRIPTION
    Creates directory structure, installs dependencies (including pywin32),
    and registers the Windows Service using app_service.py
#>

# -----------------------------
# 1️⃣ Define base directories
# -----------------------------
$AppName = "qb_shim"
$BaseDir = "C:\Program Files\$AppName"
$LogsDir = "$BaseDir\logs"
$ConfigDir = "$BaseDir\config"
$VenvDir = "$BaseDir\venv"

Write-Host "Installing $AppName service..." -ForegroundColor Cyan

# -----------------------------
# 2️⃣ Create directory structure
# -----------------------------
Write-Host "Creating directory structure..."
New-Item -ItemType Directory -Force -Path $BaseDir, $LogsDir, $ConfigDir | Out-Null

# -----------------------------
# 3️⃣ Copy application files
# -----------------------------
Write-Host "Copying application files..."
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Copy-Item -Path "$SourceDir\*" -Destination $BaseDir -Recurse -Force

# -----------------------------
# 4️⃣ Ensure Python is available
# -----------------------------
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Please install Python 3.12+ and re-run this script." -ForegroundColor Red
    exit 1
}

# -----------------------------
# ✅ Check Python version >= 3.12
# -----------------------------
$pythonVersionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonVersion = [version]$pythonVersionOutput

if ($pythonVersion -lt [version]'3.12') {
    Write-Host "❌ Python version $pythonVersion detected. Version 3.12 or higher is required." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python version $pythonVersion detected (OK)" -ForegroundColor Green

# -----------------------------
# 5️⃣ Create venv (recommended)
# -----------------------------
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvDir
}
$PythonExe = "$VenvDir\Scripts\python.exe"
$PipExe = "$VenvDir\Scripts\pip.exe"

# -----------------------------
# 6️⃣ Install dependencies
# -----------------------------
Write-Host "Installing Python dependencies..."
& $PipExe install --upgrade pip setuptools wheel
& $PipExe install -r "$BaseDir\requirements.txt"

# Ensure pywin32 is installed
& $PipExe install pywin32

# -----------------------------
# 7️⃣ Configure and install service
# -----------------------------
Write-Host "Registering Windows Service..."
& $PythonExe "$BaseDir\app_service.py" install

# -----------------------------
# 8️⃣ Start service automatically (optional)
# -----------------------------
Write-Host "Starting Windows Service..."
& $PythonExe "$BaseDir\app_service.py" start

# -----------------------------
# ✅ Done
# -----------------------------
Write-Host ""
Write-Host "✅ Installation completed successfully!" -ForegroundColor Green
Write-Host "Service name: QBShimService"
Write-Host "Logs: $LogsDir"
Write-Host ""

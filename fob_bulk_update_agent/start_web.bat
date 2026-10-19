@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3 from https://www.python.org/downloads/
  echo During setup, tick "Add python.exe to PATH", then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

set PYTHONPATH=%CD%
set HOST=127.0.0.1
set PORT=8000

echo.
echo Starting FOB CSV Cleaner at http://localhost:8000/
echo Keep this window open. Press Ctrl+C to stop.
echo.
start "" "http://localhost:8000/"
python -m uvicorn web.app:app --host %HOST% --port %PORT%
pause

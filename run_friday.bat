@echo off
setlocal
cd /d "%~dp0"
title FRIDAY - AI Desktop Assistant

:: Stop any old lingering background FRIDAY instances so updated code takes effect immediately
for /f "tokens=2" %%i in ('wmic process where "name='pythonw.exe' and CommandLine like '%%friday.py%%'" get ProcessId 2^>nul ^| findstr [0-9]') do taskkill /F /PID %%i 2>nul

if not exist .venv\Scripts\python.exe (
    echo [WARNING] Virtual environment not found. Running setup first...
    call setup.bat
)

if "%1"=="--cli" (
    .venv\Scripts\python.exe friday.py --cli
    goto :eof
)

if "%1"=="--background" (
    echo Starting FRIDAY 24/7 Silent Background System...
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0friday.py" %*
    goto :eof
)

echo Starting FRIDAY AI Assistant...
.venv\Scripts\python.exe friday.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] FRIDAY closed unexpectedly (exit code %errorlevel%).
    pause
)

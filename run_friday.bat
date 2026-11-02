@echo off
setlocal
cd /d "%~dp0"
title FRIDAY - AI Desktop Assistant

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

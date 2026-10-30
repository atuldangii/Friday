@echo off
setlocal
cd /d "%~dp0"
title FRIDAY - Desktop Assistant

if not exist .venv\Scripts\python.exe (
    echo [WARNING] Virtual environment not found. Running setup first...
    call setup.bat
)

if "%1"=="--cli" (
    .venv\Scripts\python.exe friday.py --cli
    goto :eof
)

if "%1"=="--console" (
    .venv\Scripts\python.exe friday.py %*
    goto :eof
)

echo Starting FRIDAY 24/7 Background System...
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0friday.py" %*
exit /b 0

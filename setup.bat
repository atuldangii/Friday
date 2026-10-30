@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo       FRIDAY - Windows 11 Desktop Setup
echo ========================================================

REM Check if uv is available
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Detected uv package manager. Creating optimized Python 3.12 environment...
    uv venv --python 3.12 .venv
    echo [INFO] Installing dependencies via uv...
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt
    goto finish
)

REM Fallback to standard Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on PATH. Please install Python 3.11 or 3.12.
    pause
    exit /b 1
)

echo [INFO] Creating Python virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [INFO] Activating virtual environment and upgrading pip...
call .venv\Scripts\activate
python -m pip install --upgrade pip

echo [INFO] Installing required dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation encountered errors.
    pause
    exit /b 1
)

:finish
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [INFO] Created .env configuration from .env.example.
    )
)

echo ========================================================
echo [SUCCESS] FRIDAY is ready!
echo Launch with: run_friday.bat
echo ========================================================
pause

@echo off
setlocal
cd /d "%~dp0"
echo Adding FRIDAY to Windows Startup...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /y "%~dp0run_friday_background.vbs" "%STARTUP_FOLDER%\FridayAssistant.vbs"
if %errorlevel% equ 0 (
    echo [SUCCESS] FRIDAY will now automatically run in the background whenever you start your PC!
) else (
    echo [ERROR] Failed to add to startup folder.
)
pause


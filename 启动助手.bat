@echo off
title Diablo4 Game Assistant
cd /d "%~dp0"

echo ==================================================
echo            Diablo4 Game Assistant
echo ==================================================
echo.
echo Starting, please wait...
echo   - Auto detect and start SDK server (if not running)
echo   - Auto launch the assistant main program
echo   - Drag window by clicking the top header area
echo.
echo Closing this window will NOT close the assistant.
echo To exit, close the main program window.
echo ==================================================
echo.

REM Prefer project-local Python, fall back to system Python
if exist "pylibs\python.exe" (
    set "PYTHON=pylibs\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

REM Launch main program (auto-starts SDK server if needed)
"%PYTHON%" main.py

REM Pause on abnormal exit so errors are visible
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==================================================
    echo Program exited with error code: %ERRORLEVEL%
    echo ==================================================
    pause
)

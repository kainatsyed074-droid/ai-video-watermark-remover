@echo off
setlocal enabledelayedexpansion

echo ====================================================
echo   Starting AI Video Watermark Remover...
echo ====================================================

:: Locate Python
set "PYTHON_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else (
    set "PYTHON_EXE=python"
)


echo Starting local web server...
:: Open browser in background after 2 seconds
start "" powershell -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:5000'"

:: Start Flask App
"!PYTHON_EXE!" app.py

pause

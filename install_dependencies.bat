@echo off
setlocal enabledelayedexpansion

echo ====================================================
echo   AI Video Watermark Remover - Environment Setup
echo ====================================================
echo.

:: 1. Check for Python
set "PYTHON_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        echo Python is not installed. Installing Python via winget...
        winget install Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements
        if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        ) else (
            echo Failed to automatically locate Python. Please install Python 3.10+ and re-run.
            pause
            exit /b 1
        )
    )
)


echo Using Python: !PYTHON_EXE!
echo.

:: 2. Install requirements
echo Installing Python dependencies (Flask, OpenCV, NumPy, Pillow)...
"!PYTHON_EXE!" -m pip install --upgrade pip
"!PYTHON_EXE!" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo   Environment Setup Successfully Completed!
echo   You can now launch the app by running start.bat
echo ====================================================
pause

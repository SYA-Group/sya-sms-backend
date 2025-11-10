@echo off
echo ==========================================
echo      Starting Flask Server Environment
echo ==========================================

REM Step 1: Move to the project directory
cd /d %~dp0

REM Step 2: Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Step 3: Activate virtual environment
call venv\Scripts\activate

REM Step 4: Install dependencies
if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
) else (
    echo No requirements.txt found. Skipping dependency install.
)

REM Step 5: Start Flask app in background
echo ------------------------------------------
echo Starting Flask server...
echo ------------------------------------------
start "" python app.py

REM Step 6: Start NGINX reverse proxy for HTTPS redirection
echo ------------------------------------------
echo Starting NGINX (reverse proxy for HTTPS)...
echo ------------------------------------------

set NGINX_PATH=C:\nginx
set NGINX_CONF=%NGINX_PATH%\conf\nginx.conf
set NGINX_LOGS=%NGINX_PATH%\logs

if exist "%NGINX_PATH%\nginx.exe" (
    REM Ensure logs folder exists
    if not exist "%NGINX_LOGS%" (
        mkdir "%NGINX_LOGS%"
    )

    REM Stop existing NGINX if running
    "%NGINX_PATH%\nginx.exe" -s stop >nul 2>&1

    REM Start NGINX with explicit config path and working directory
    pushd "%NGINX_PATH%"
    "%NGINX_PATH%\nginx.exe" -c "%NGINX_CONF%"
    popd

    echo NGINX started successfully with config: %NGINX_CONF%
) else (
    echo WARNING: NGINX not found at %NGINX_PATH%.
    echo Please install or update the NGINX_PATH variable.
)


REM Step 8: Keep window open after exit
pause

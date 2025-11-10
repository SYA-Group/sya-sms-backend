@echo off
echo ==========================================
echo      Starting Celery Worker
echo ==========================================

REM Step 1: Navigate to project directory
cd /d %~dp0

REM Step 2: Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found, creating one...
    python -m venv venv
)

REM Step 3: Activate virtual environment
call venv\Scripts\activate

REM Step 4: Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Step 5: Start Celery worker
echo ------------------------------------------
echo Starting Celery worker...
echo ------------------------------------------
celery -A celery_app.celery_app worker --loglevel=info

REM Step 6: Keep window open after worker stops
pause

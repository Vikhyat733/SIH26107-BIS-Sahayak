@echo off
echo Starting BIS Sahayak Backend...
cd backend

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run the setup steps first.
    pause
    exit /b
)

call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000

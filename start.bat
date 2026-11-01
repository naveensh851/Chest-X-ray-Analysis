@echo off
echo ====================================================
echo Starting AI X-ray Diagnosis Application
echo ====================================================

echo [1/2] Starting Backend Server (FastAPI + EfficientNetB0)...
start "X-Ray Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting Frontend Server (React + Vite)...
start "X-Ray Frontend (Vite)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Application is starting!
echo Frontend: http://localhost:5173
echo Backend:  http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo ====================================================

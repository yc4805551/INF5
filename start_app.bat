@echo off
cd /d %~dp0

echo ==========================================
echo       INFV5 Application Launcher
echo ==========================================

REM 0. Cleanup Old Processes
echo [INFO] Stopping existing Python (Backend) and Node (Frontend) processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 1 >nul

REM 1. Environment Setup (Auto-Detection & Creation)
if not exist "backend\venv" (
    echo [INFO] Virtual environment not found in backend\venv.
    echo [INFO] Creating virtual environment...
    cd backend
    python -m venv venv
    cd ..
    echo [SUCCESS] Virtual environment created.
    echo [INFO] Please run 'install_deps.bat' to install dependencies for the first time!
) else (
    echo [INFO] Virtual environment found in backend\venv.
)

REM 2. Start Services
echo Starting Backend...
start "Backend Server" cmd /k "cd backend && venv\Scripts\python.exe app.py"

echo Starting Frontend...
start "Frontend Client" cmd /k "cd frontend && npm run dev"

echo ==========================================
echo Application started!
echo Backend running on port 5179
echo Frontend running on port 5178
echo External Access: http://www.yc01.top:5178
echo ==========================================
pause

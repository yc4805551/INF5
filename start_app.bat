@echo off
cd /d %~dp0
echo Starting Backend...
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No virtual environment found, using system python...
)

echo Starting Backend...
start "Backend Server" cmd /k "cd backend && "%~dp0.venv\Scripts\python.exe" app.py"

echo Starting Frontend...
start "Frontend Client" cmd /k "cd frontend && npm run dev"

echo Application started!
echo Backend running on port 5179
echo Frontend running on port 5178
echo External Access: http://www.yc01.top:5178
pause

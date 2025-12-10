@echo off
cd /d %~dp0
echo Starting Backend (GLY Custom - Anaconda)...

echo Running Health Check...
"C:\ProgramData\anaconda3\python.exe" backend/check_health.py
if %errorlevel% neq 0 (
    echo [WARNING] Health Check Failed! 
    echo Proceeding...
)

start "Backend Server" cmd /k "cd backend && "C:\ProgramData\anaconda3\python.exe" app.py"

echo Starting Frontend...
start "Frontend Client" cmd /k "cd frontend && npm run dev"

echo Application started!
echo Backend running on port 5179
echo Frontend running on port 5178
pause

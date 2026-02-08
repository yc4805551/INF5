@echo off
cd /d %~dp0
echo Installing Backend Dependencies...
if exist "backend\venv" (
    backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
) else (
    echo [ERROR] Virtual environment not found. Please run start_app.bat first to create it.
)
pause

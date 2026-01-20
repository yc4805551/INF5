@echo off
REM 自动识别当前目录
set "PROJECT_DIR=%~dp0.."

echo 正在启动前端服务...
start "web" cmd /k "cd /d "%PROJECT_DIR%\frontend" && npm run dev"

echo 正在启动后端服务...
start "backserver" cmd /k "cd /d "%PROJECT_DIR%\backend" && "%PROJECT_DIR%\.venv\Scripts\python.exe" app.py"

echo END
    
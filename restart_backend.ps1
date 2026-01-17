
Write-Host "Stopping all Python processes..."
taskkill /F /IM python.exe
Start-Sleep -Seconds 2

Write-Host "Clearing Python Cache (__pycache__)..."
Get-ChildItem -Path "backend" -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Write-Host "Cache Cleared."

Write-Host "Starting Backend..."
$env:PYTHONPATH = "backend"
python backend/app.py

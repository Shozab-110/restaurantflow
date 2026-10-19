@echo off
cd /d "%~dp0"
echo Enable RestaurantFlow TCP port 8001 for local-subnet devices only.
echo Windows will request administrator approval. PostgreSQL stays private.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\enable_lan.ps1"
pause

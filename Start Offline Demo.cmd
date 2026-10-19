@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Complete docs\GETTING_STARTED.md once first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\demo_server.py" %*
pause

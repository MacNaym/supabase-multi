\
@echo off
setlocal
cd /d "%~dp0"

if not exist "mcp\.venv\Scripts\python.exe" (
  echo Supabase Multi is not set up yet.
  echo Running setup...
  call setup.bat
  if errorlevel 1 exit /b 1
)

echo Starting Supabase Multi...
start "Supabase Multi" python "local-ui\server.py"

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"

endlocal

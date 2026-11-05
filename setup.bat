\
@echo off
setlocal
cd /d "%~dp0"

echo [Supabase Multi] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer is required.
  exit /b 1
)

echo [Supabase Multi] Creating MCP virtual environment...
if not exist "mcp\.venv\Scripts\python.exe" (
  python -m venv "mcp\.venv"
  if errorlevel 1 exit /b 1
)

echo [Supabase Multi] Upgrading pip...
"mcp\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo [Supabase Multi] Installing MCP dependencies...
"mcp\.venv\Scripts\python.exe" -m pip install -r "mcp\requirements.txt"
if errorlevel 1 exit /b 1

if not exist "registry.json" (
  if exist "registry.example.json" (
    copy /y "registry.example.json" "registry.json" >nul
    echo [Supabase Multi] Created registry.json from registry.example.json
  )
)

echo.
echo Supabase Multi setup completed.
echo Run start-supabase-multi.bat to open the dashboard.
endlocal

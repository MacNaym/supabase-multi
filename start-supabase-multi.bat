@echo off
setlocal
cd /d "%~dp0"

if not exist "mcp\.venv\Scripts\python.exe" (
  echo Supabase Multi is not set up yet.
  echo Running setup...
  call setup.bat
  if errorlevel 1 exit /b 1
)

echo [Supabase Multi] Checking local control plane...
"mcp\.venv\Scripts\python.exe" "scripts\runtime_guard.py" > "%TEMP%\supabase-multi-runtime.txt" 2>&1
set "RUNTIME_GUARD_EXIT=%ERRORLEVEL%"
set /p RUNTIME_GUARD_RESULT=<"%TEMP%\supabase-multi-runtime.txt"
del "%TEMP%\supabase-multi-runtime.txt" >nul 2>&1

if "%RUNTIME_GUARD_EXIT%"=="0" (
  echo [Supabase Multi] Control plane is already running and current.
  if /I not "%SUPABASE_MULTI_NO_BROWSER%"=="1" start "" "http://127.0.0.1:8765"
  exit /b 0
)

if "%RUNTIME_GUARD_EXIT%"=="2" (
  echo [Supabase Multi] Stale control plane stopped. Reloading current code...
)

if "%RUNTIME_GUARD_EXIT%"=="3" (
  echo ERROR: A stale process is listening on port 8765 and could not be stopped safely.
  exit /b 1
)

echo [Supabase Multi] Starting local control plane...
start "Supabase Multi" /min "mcp\.venv\Scripts\python.exe" "local-ui\server.py"

echo [Supabase Multi] Waiting for readiness...
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 40;$i++){ try { $r=Invoke-RestMethod 'http://127.0.0.1:8765/api/state?local=1' -TimeoutSec 1; if($r.ok){$ok=$true;break} } catch {}; Start-Sleep -Milliseconds 250 }; if(-not $ok){exit 1}"
if errorlevel 1 (
  echo ERROR: Supabase Multi control plane did not become ready on http://127.0.0.1:8765
  exit /b 1
)

echo [Supabase Multi] Ready.
if /I not "%SUPABASE_MULTI_NO_BROWSER%"=="1" start "" "http://127.0.0.1:8765"

endlocal

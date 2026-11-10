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
powershell -NoProfile -Command "try { $r=Invoke-RestMethod 'http://127.0.0.1:8765/api/state?local=1' -TimeoutSec 2; if($r.ok){exit 0} } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 (
  echo [Supabase Multi] Control plane is already running.
  if /I not "%SUPABASE_MULTI_NO_BROWSER%"=="1" start "" "http://127.0.0.1:8765"
  exit /b 0
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

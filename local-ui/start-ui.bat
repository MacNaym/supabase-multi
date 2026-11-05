@echo off
setlocal
cd /d "%~dp0"
echo Avvio Supabase Multi Local Admin v3.1...
python server.py
if errorlevel 1 (
  echo.
  echo ERRORE: impossibile avviare il server.
  pause
)

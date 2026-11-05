@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [Supabase Multi MCP] Virtual environment not found.
  echo Run ..\setup.bat first.
  exit /b 1
)

".venv\Scripts\python.exe" server.py
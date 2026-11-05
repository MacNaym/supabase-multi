@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\mcp.exe" (
  echo [Supabase Multi MCP] MCP CLI not found in local virtual environment.
  echo Run ..\setup.bat first.
  exit /b 1
)

".venv\Scripts\mcp.exe" dev server.py
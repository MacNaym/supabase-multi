# Troubleshooting

## Dashboard does not start

```powershell
python --version
python .\local-ui\server.py
```

Then open `http://127.0.0.1:8765`.

## MCP SDK import fails

```powershell
.\mcp\.venv\Scripts\python.exe -c "from mcp.server import MCPServer; print('MCP SDK OK')"
```

## Supabase Multi MCP import fails

```powershell
cd .\mcp
.\.venv\Scripts\python.exe -c "import server; print('SUPABASE MULTI MCP IMPORT OK')"
```

## MCP tools are not visible

```powershell
cd .\mcp
.\.venv\Scripts\mcp.exe dev server.py
```

Inspector is for troubleshooting only.

## Project status is UNKNOWN

Check:

- project PAT exists;
- PAT permissions are sufficient;
- `project_ref` is correct;
- exact account CLI profile works;
- project is visible to that account.

Use `verify_access`.

## Wrong account opens in browser

Verify the account's isolated browser profile and reopen the project through Supabase Multi.

## Orphaned secret remains

This is expected after project deletion.

Review it under `Status → Orphaned secrets` before deleting it.

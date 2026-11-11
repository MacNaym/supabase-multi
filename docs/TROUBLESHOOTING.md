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

## SQL proxy returns HTTP 403

Supabase Multi proxies SQL through the official project-scoped Supabase MCP. Current code sends an explicit `User-Agent` because Python `urllib` requests without one may be rejected by the remote edge layer.

If a 403 appears:

1. update to the latest Supabase Multi revision;
2. verify the project's PAT can read the project through the Supabase Management API;
3. verify the same PAT can initialize the official Supabase MCP endpoint for that `project_ref`;
4. confirm the target is not configured `read_only` before using `execute_sql`.

Do not work around a 403 by exposing or logging the PAT.

## SQL writes are blocked

`execute_sql(target, query, confirm=true)` is intentionally write-capable only when both conditions are true:

- the caller explicitly sends `confirm=true`;
- the target is not configured `read_only`.

Use `query_sql` for forced read-only SQL.

## Client shows an old tool list

The current server exposes 31 tools. Some MCP/plugin clients cache tool metadata for an existing session.

- start a new client conversation/session after refreshing MCP metadata;
- use `get_capabilities` and `invoke_capability` for the stable live-capability gateway;
- verify the server itself with MCP Inspector or a fresh stdio handshake before assuming the local server is stale.

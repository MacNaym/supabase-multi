# Supabase Multi MCP

This directory contains the MCP control-plane server for Supabase Multi.

> A local Supabase control plane for humans and AI agents managing multiple accounts and projects.

## What this MCP does

Supabase Multi MCP resolves and manages the local account/project configuration. It is the **control plane/router**, not a replacement for the official Supabase MCP server.

Use Supabase Multi to determine the correct account, project, `project_ref`, PAT environment-variable name and MCP target. Use the official Supabase MCP server to execute database/project operations.

## Requirements

- Windows 10/11
- Python 3.11+
- the Supabase Multi project root
- Supabase CLI when CLI-backed discovery/fallback is wanted

## Install

Run the project-level setup from the repository root:

```powershell
.\setup.bat
```

This creates `mcp\.venv` and installs the MCP SDK there. Do not install the dependency globally just to run Supabase Multi.

## Run over stdio

From the repository root:

```powershell
.\mcp\.venv\Scripts\python.exe .\mcp\server.py
```

Normal MCP clients should launch that command automatically.

The MCP process starts the local Supabase Multi control plane on `127.0.0.1:8765` if needed. Readiness and normal MCP state reads use the lightweight `/api/state?local=1` endpoint so they do not wait on remote Supabase checks.

## Test with MCP Inspector

Inspector is for development/troubleshooting only:

```powershell
.\mcp\inspect-mcp.bat
```

## Security invariants

- Raw PAT values are never returned by MCP.
- PAT setup through MCP uses `source_env` and copies the secret locally between environment variables.
- Destructive tools require `confirm=true`.
- `resolve_project` never guesses: an ambiguous result must be surfaced to the user for confirmation.
- The local control plane binds to `127.0.0.1`.

## Tool groups

### Read / routing

`get_dashboard`, `list_accounts`, `get_account`, `list_projects`, `get_project`, `resolve_project`, `verify_access`, `query_sql`, `execute_sql`, `list_orphaned_secrets`

### Operations

`sync_mcp`, `doctor`, `sync_and_doctor`, `open_project`, `discover_account`

### Account administration

`create_or_update_account`, `delete_account`, `connect_account_cli`, `disconnect_account_cli`, `copy_discovery_pat_from_env`, `clear_discovery_pat`

### Project administration

`import_projects`, `create_or_update_project`, `reassign_project`, `delete_project`, `copy_project_pat_from_env`, `clear_project_pat`

### Secret cleanup

`delete_orphaned_secret`, `clean_all_orphaned_secrets`

## Automated tests

The repository CI contains regression tests for:

- fast local-state reads used by MCP;
- MCP public-field sanitization;
- destructive-action confirmation;
- local-state operation without remote Supabase checks;
- clean Windows installation/startup smoke testing;
- real MCP stdio initialize/tool-discovery startup;
- SQL proxy read-only/write safety boundaries.

## SQL through Supabase Multi

`query_sql(target, query)` executes through the official project-scoped Supabase MCP in forced read-only mode.

`execute_sql(target, query, confirm=true)` is write-capable, requires explicit confirmation, and refuses projects configured as read-only.

Resolve the exact target before either tool. Raw PAT values remain local and are never returned by Supabase Multi MCP.

## Codex

See [../docs/codex.md](../docs/codex.md) for direct stdio, Secure MCP Tunnel, startup checks, and current Codex-plugin packaging guidance.

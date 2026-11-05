# Supabase Multi MCP — Preview

This is the MCP layer for Supabase Multi.

Tagline:

> A local Supabase control plane for humans and AI agents managing multiple accounts and projects.

## Requirements

- Windows
- Python 3.11+
- Supabase Multi project root containing `registry.json`, `scripts/`, `local-ui/`, and this `mcp/` folder
- Supabase CLI for CLI-backed account discovery/fallback

## Install

```powershell
cd mcp
python -m pip install -r requirements.txt
```

## Test with MCP Inspector

Run:

```powershell
mcp dev server.py
```

or double-click `inspect-mcp.bat`.

## Run over stdio

```powershell
python server.py
```

The MCP process automatically starts the local Supabase Multi control plane on `127.0.0.1:8765` if it is not already running.

## Security

- Raw PAT values are never returned by the MCP.
- PAT setup through MCP uses `source_env` and copies the secret locally between environment variables.
- Destructive tools require `confirm=true`.
- `resolve_project` never guesses: it returns `ambiguous` with candidates when more than one project matches.

## Tool groups

### Read / routing
`get_dashboard`, `list_accounts`, `get_account`, `list_projects`, `get_project`, `resolve_project`, `verify_access`, `list_orphaned_secrets`

### Operations
`sync_mcp`, `doctor`, `sync_and_doctor`, `open_project`, `discover_account`

### Account administration
`create_or_update_account`, `delete_account`, `connect_account_cli`, `disconnect_account_cli`, `copy_discovery_pat_from_env`, `clear_discovery_pat`

### Project administration
`import_projects`, `create_or_update_project`, `reassign_project`, `delete_project`, `copy_project_pat_from_env`, `clear_project_pat`

### Secret cleanup
`delete_orphaned_secret`, `clean_all_orphaned_secrets`

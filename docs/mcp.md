# MCP

Supabase Multi exposes its control plane through MCP.

## Responsibilities

Supabase Multi MCP handles:

- account/project resolution;
- project metadata;
- status;
- PAT presence;
- CLI profile routing;
- browser routing;
- MCP target selection;
- local administration.

The official Supabase MCP server handles project-level operations such as SQL, schema inspection, migrations, logs, advisors, and Edge Functions.

## Safety rule

Never guess a target.

If `resolve_project` returns `ambiguous`, the agent must ask the user which account/project to use.

## Destructive tools

Destructive operations require `confirm=true`.

## Secrets

MCP tools may return an environment-variable name and whether a secret exists.

They must not return raw PAT values.

## Development

From `mcp/`:

```powershell
.\.venv\Scripts\mcp.exe dev server.py
```

The expected current server exposes 27 tools.

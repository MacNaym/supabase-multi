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

The official Supabase MCP server remains the project-level executor for schema inspection, migrations, logs, advisors, Edge Functions, and database work. Supabase Multi can now proxy SQL to its official `execute_sql` tool after resolving an exact target.

## Safety rule

Never guess a target.

If `resolve_project` returns `ambiguous`, the agent must ask the user which account/project to use.

## SQL

`query_sql(target, query)` always proxies to the official Supabase MCP with `read_only=true`.

`execute_sql(target, query, confirm=true)` uses the write-capable official SQL path only when the Supabase Multi target is not configured read-only. The local HTTP endpoint independently requires `confirm=true`.

The project PAT is read locally from its configured environment variable and is never returned to the calling agent.

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

The expected current server exposes 29 tools.

## Codex and other harnesses

The server speaks standard MCP over stdio. CI launches a real MCP client, initializes the server and lists tools, which verifies the transport independently of Codex. Client-specific integration is documented in [codex.md](codex.md).

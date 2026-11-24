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

The SQL proxy talks to the official Supabase MCP over HTTP and sends an explicit `User-Agent` for compatibility with the remote edge layer. A real write/read smoke test has verified the write-capable path end-to-end.

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

The expected current server exposes 31 tools.

## Codex and other harnesses

The server speaks standard MCP over stdio. CI launches a real MCP client, initializes the server and lists tools, which verifies the transport independently of Codex. Client-specific integration is documented in [codex.md](codex.md).

## Live capability gateway

ChatGPT custom MCP plugins may keep a frozen snapshot of tool metadata until an explicit Refresh is approved in ChatGPT. Supabase Multi therefore exposes two stable tools designed to avoid repeated metadata churn:

- `get_capabilities()` returns the live server-side capability registry and generation;
- `invoke_capability(operation, arguments, confirm=false)` executes one advertised capability through a server-side whitelist.

The gateway schema is intentionally stable. New operations can be added to the live registry without changing the gateway tool schema, so clients that already know these two tools can discover and use future capabilities without requiring a new tool definition.

Write-capable live operations still require `confirm=true`, and all existing target/read-only/PAT safety rules remain enforced downstream.


### Edge Functions through the live gateway

The live capability registry also exposes:

- `list_edge_functions(target)`
- `get_edge_function(target, function_slug)`
- `deploy_edge_function(target, name, files, entrypoint_path, verify_jwt, import_map_path?)`
- `delete_edge_function(target, function_slug)`

List, get, and deploy are proxied to the official project-scoped Supabase MCP. Delete uses the Supabase Management API because the official Supabase MCP currently exposes no `delete_edge_function` tool.

Read operations require the PAT's Edge Functions read permission. Deploy/delete require Edge Functions read-write permission, explicit `confirm=true`, and a Supabase Multi target that is not configured read-only.


## Database backup V1 through the live gateway

The live registry exposes:

- `backup_database(target, mode="full", destination?, db_url_env?)`
- `verify_database_backup(path)`

Backup modes are `schema`, `data`, and `full`. Full mode creates `roles.sql`, `schema.sql`, and `data.sql`, plus a `manifest.json` containing file sizes and SHA-256 hashes.

Backups use the current Supabase CLI `db dump --remote=...` flow. Supabase Multi never stores or returns the database connection string. It resolves the connection-string environment variable in this order:

1. explicit `db_url_env` argument;
2. project `db_url_env` in `registry.json`;
3. derived name `SUPABASE_DB_URL_<TARGET>`.

For example, `example-prod` defaults to `SUPABASE_DB_URL_EXAMPLE_PROD`.

The default local destination is `~/SupabaseMultiBackups/<target>/<UTC timestamp>/`. Set `SUPABASE_MULTI_BACKUP_DIR` to change the default root, or pass `destination` for one call.

Database backups do not include the actual files stored through Supabase Storage; they cover the logical Postgres database. Storage-object backup is intentionally outside V1.

`verify_database_backup` recomputes sizes and SHA-256 hashes and reports any missing or modified file.

## Local-first runtime and optional headless backend

The normal Windows runtime remains local-first:

- stdio MCP is the default transport;
- the desktop control plane/dashboard remains on `127.0.0.1:8765`;
- Supabase Multi can be started only when needed.

The server also contains a portable headless backend and optional Streamable HTTP transport for advanced deployments. Transport selection and backend selection are intentionally separate so enabling Streamable HTTP does not silently change local routing behavior.

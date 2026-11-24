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


## Database backup and restore module 1.5 through the live gateway

The live registry exposes:

- `backup_database(target, mode="full", destination?)`
- `list_database_backups(target, destination?)`
- `verify_database_backup(path)`
- `validate_database_backup(path)`
- `import_database_backup(path)`

Backup modes are `schema`, `data`, and `full`. Full mode creates `roles.sql`, `schema.sql`, and `data.sql`, plus a `manifest.json` containing file sizes and SHA-256 hashes.

Backups use the current Supabase CLI `db dump --remote=<project_ref>` flow. Supabase Multi takes the project ref and the existing project PAT from the registry/environment, then passes the PAT to the CLI through `SUPABASE_ACCESS_TOKEN`. The CLI can create a temporary database login, so a database URL or database password is not normally required.

If temporary-login authentication fails, Supabase Multi optionally retries with a database password. The fallback variable defaults to `SUPABASE_DB_PASSWORD_<TARGET>` or may be overridden by a project's `db_password_env`. Raw PATs and database passwords are never written to the registry, manifest, or MCP response.

The backup destination is resolved in this order:

1. explicit `destination` argument;
2. project `backup_dir` saved from the local dashboard;
3. `SUPABASE_MULTI_BACKUP_DIR`;
4. `~/SupabaseMultiBackups`.

The local dashboard has a dedicated **Backup** view with project selection, backup mode, native Windows folder picker, per-project default destination, backup history, SHA-256 verification, and **Open folder**.

Database backups do not include the actual files stored through Supabase Storage; they cover the logical Postgres database. They also do not necessarily include Supabase platform configuration, Auth state, Edge Functions, webhooks, cron jobs or external integrations.

`verify_database_backup` recomputes sizes and SHA-256 hashes and reports any missing or modified file.

`validate_database_backup` also performs non-executing, streaming SQL/dump-text checks. Its report distinguishes integrity, heuristic structure, and `restore_tested`; validation never executes SQL and cannot prove that a dump is safe or restorable. `import_database_backup` validates an external folder in place. It does not copy a dump, write the registry, persist SQL, or return credentials.

The dashboard can run a local Test Restore only after the operator marks a full validated backup trusted and selects an already-installed official Supabase PostgreSQL image pinned by digest. The disposable container has network disabled, no published ports, no host bind mounts, and receives no host PAT or database password. It restores roles, schema, then data with `ON_ERROR_STOP`, cleans itself up, and reports tables, estimated rows, functions, constraints, extensions and RLS. This is a local, non-production test only.

Remote restore execution is not a live capability in 3.10.0. Remote planning/preflight fails closed unless the destination resolves to one exact account/project/ref, is explicitly restore-enabled, is non-production, writable, and differs from the source. It does not make remote writes.

## Local-first runtime and optional headless backend

The normal Windows runtime remains local-first:

- stdio MCP is the default transport;
- the desktop control plane/dashboard remains on `127.0.0.1:8765`;
- Supabase Multi can be started only when needed.

The server also contains a portable headless backend and optional Streamable HTTP transport for advanced deployments. Transport selection and backend selection are intentionally separate so enabling Streamable HTTP does not silently change local routing behavior.

### IPv4 session pooler fallback (Backup V1.2)

Backups default to `auto`: try the exact project ref first, then resolve its primary shared session pooler through the Management API if the CLI reports IPv6 is unavailable. Optional per-project registry field `backup_connection_mode` accepts `auto`, `direct`, or `session-pooler`. The fallback requires `database_pooling_config_read` and, unless a project database password is already configured, `database_write` to mint a temporary CLI login. Temporary credentials are not written to the registry or manifest; the connection URL is passed to the local CLI process and is never returned in the API response. Local processes with sufficient privileges may inspect command-line arguments. A live backup and restore test is required to establish compatibility.

## Dashboard backup jobs (V1.3)

The dashboard uses `POST /api/backup-start` and polls `GET /api/backup-job`. The server retains the latest job in memory, so browser refresh does not lose its status while the server remains running. Progress counts completed phases, not percentage of database bytes. File sizes may remain unchanged while the CLI works. Server reachability is not proof of dump activity. One dashboard job at a time; MCP backup calls retain their synchronous behavior and are not tracked by this dashboard job manager. Do not restart the server during a backup. Job status is not durable across process restarts. Each CLI dump has a one-hour timeout.

### Backup validation and import (3.10.0 development)

Select Import backup in the Backup tab to choose an existing folder containing manifest.json. This is a read-only in-place import for inspection, not a file copy or a database restore. Verify in history also runs advanced validation. The report includes source metadata, SHA-256, file sizes and heuristic UTF-8/SQL text checks. No SQL is executed. Validating a dump is not proof of authenticity, safety or restorability; only use trusted dumps. Partial backups can pass validation but are not full restore candidates. No PAT is needed for local validation. Revalidate before any future restore.

### Isolated restore test (development)

Validate a trusted full backup, enter a locally installed `supabase/postgres@sha256:...` image digest, confirm trust and click Test restore. The temporary container has no published ports or network. The report provides an inventory, not a source comparison or guarantee of application recovery. No remote restore is enabled. Job status lives in memory; do not stop the server during a restore. A failed cleanup reports the container name for manual review. Use only trusted SQL and images.

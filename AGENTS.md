# AGENTS.md — Supabase Multi

These rules apply to AI agents working in this repository.

## Core invariant

Supabase Multi is a local control plane for multiple Supabase accounts and projects.

The UI and MCP server must use the same underlying control-plane state.

## Supabase routing

- Never guess a Supabase account, project, `project_ref`, PAT environment variable, or MCP target.
- Resolve the project through Supabase Multi first.
- Prefer repository mapping through `.supabase-target.json`.
- If exactly one project matches, proceed with that target.
- If multiple projects match, **ask the user which account/project to use**.
- Do not silently select production.
- Do not convert ambiguity into a generic internal error.

## Secrets

- Never print, log, return, commit, or place raw PAT values in documentation.
- `registry.json` stores secret environment-variable names, not secret values.
- PAT values belong in Windows User Environment variables.
- Do not inject PAT values into URLs, browser cookies, or browser local storage.
- Never commit `.env*`, `registry.json`, `oauth-sessions.dat`, browser profiles, backups, or `mcp/.venv/`.

## Destructive operations

Destructive MCP operations require explicit confirmation.

Examples:
- delete account;
- delete project;
- disconnect CLI;
- clear PAT;
- delete orphaned secret;
- clean all orphaned secrets.

Do not weaken confirmation requirements.

For SQL:
- use `query_sql` for read-only queries;
- never emulate writes through `query_sql`;
- `execute_sql` requires explicit user approval and `confirm=true`;
- refuse write-capable SQL when the resolved target is configured read-only;
- never return or log the project PAT.

## Supabase MCP relationship

Supabase Multi MCP is the control plane and resolver.

It does not replace the official Supabase MCP server for actual database/project operations.

Typical flow:

```text
agent
  -> Supabase Multi MCP
  -> resolve exact target
  -> official Supabase MCP for that target
  -> Supabase project
```

Supabase Multi may proxy narrowly defined operations such as SQL to the official project-scoped MCP after resolution. This does not change the control-plane/executor boundary.

## Verification

When changing routing, authentication, PAT checks, deletion behavior, or MCP tools:

1. test the specific behavior;
2. test the failure mode;
3. test that no secret value is returned;
4. update documentation if user-visible behavior changed.

## Live capability gateway

- If an expected explicit MCP tool is missing, call `get_capabilities` before declaring the operation unavailable.
- Use `invoke_capability` only with an operation advertised by `get_capabilities`.
- Never bypass confirmation requirements through the gateway.
- The gateway must remain whitelist-based; do not add arbitrary shell, URL, SQL-target, or function dispatch.

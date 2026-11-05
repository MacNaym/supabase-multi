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

## Verification

When changing routing, authentication, PAT checks, deletion behavior, or MCP tools:

1. test the specific behavior;
2. test the failure mode;
3. test that no secret value is returned;
4. update documentation if user-visible behavior changed.

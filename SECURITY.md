# Security Policy

Supabase Multi manages local metadata that can point to privileged Supabase credentials. Security issues involving credential exposure, unsafe project routing, destructive MCP behavior, browser-session isolation, or unintended network exposure are treated as high priority.

## Supported versions

Until the first stable release, only the latest published pre-release is supported.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a suspected vulnerability.

Use GitHub private vulnerability reporting / Security Advisories when available. Do not disclose suspected vulnerabilities in public issues.

Include:
- affected version or commit;
- operating system;
- reproduction steps;
- expected and observed behavior;
- whether any credential value was exposed;
- whether the issue requires local access.

## Security invariants

Supabase Multi is designed around these rules:

1. Raw PAT values are never stored in `registry.json`.
2. Raw PAT values must never be returned by MCP tools.
3. `registry.json`, `.env*`, browser profiles, OAuth session data, backups, and virtual environments must not be committed.
4. The local dashboard binds to `127.0.0.1`.
5. Destructive MCP operations require explicit confirmation.
6. Account deletion is blocked while projects are still associated with the account.
7. Ambiguous project resolution must never silently pick a target.
8. Browser sessions, Supabase CLI profiles, and PAT authentication remain separate.
9. PATs must never be injected into URLs, cookies, or browser local storage.
10. Public releases must pass a secret scan before publication.

## Production usage

When using AI tools against production Supabase projects:

- prefer project-scoped credentials;
- use read-only access whenever possible;
- keep the human approval layer for destructive operations;
- verify the resolved target before schema or data changes;
- review official Supabase MCP security guidance.

Supabase Multi is an independent project and does not alter Supabase's own security model.



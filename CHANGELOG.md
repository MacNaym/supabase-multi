## Backup 1.3 development

- Dashboard background job with phase progress, elapsed time, bytes on disk and polling across browser refreshes.
- Automatically verify backup hashes after generation; retain explicit Verify action.
- Preserve synchronous MCP backup API. Dashboard job state is in-memory; cross-process job coordination is not yet implemented.

## Supabase Multi 3.9.1 (development)

- Single product version from runtime_identity; dashboard and MCP report the same version. Backup module numbering and external Supabase CLI version are separate.
- 3.9.0 was the dashboard label for Backup V1.2, not the Supabase CLI version. Real backup tested with CLI 3.3.0.

## Backup V1.2

- Automatic IPv4 session pooler fallback with project-scoped API lookup and temporary CLI login; regression coverage for routing and error redaction.

- Separate account and project selection, explicit project ref, backend ownership validation and project-specific history.
- Explicit CLI profile for backup subprocesses; no password fallback for unrelated errors.

## 2026-11-24

### Added
- Live `backup_database` capability with `schema`, `data`, and `full` modes.
- Full logical backups create roles, schema, data, and a SHA-256 manifest.
- Live `verify_database_backup` capability detects missing or modified backup files.
- Backup runtime uses `db dump --remote=<project_ref>` with the existing project PAT passed as `SUPABASE_ACCESS_TOKEN`; no database URL is required.
- Optional database-password fallback uses `SUPABASE_DB_PASSWORD_<TARGET>` (or project `db_password_env`) only if temporary login fails.
- Added `list_database_backups` live capability and per-project default `backup_dir`.
- Added a local Backup dashboard with native folder picker, create/list/verify/open-folder actions, and per-project destination persistence.
- Default backup location remains `~/SupabaseMultiBackups`, with `SUPABASE_MULTI_BACKUP_DIR` and per-call destination overrides.

﻿# Changelog

All notable changes to Supabase Multi will be documented in this file.

The format is based on Keep a Changelog and the project follows Semantic Versioning once stable releases begin.

## [Unreleased]

## [3.10.0] - 2026-11-24

### Added
- Backup & Restore module 1.5.0 with strict full/schema/data manifest inventory, SHA-256 and byte-size checks, structural SQL-dump heuristics, and explicit integrity/structure/restoreability reporting.
- Read-only in-place external backup import through the dashboard and live MCP capability gateway; it does not copy or execute SQL.
- Disposable local restore test using an already-installed official Supabase PostgreSQL digest, Docker network isolation, no published ports or host mounts, ordered roles/schema/data execution, timeout handling, cleanup, and inventory reporting.
- Remote destination planning and read-only TLS preflight guards for exact explicitly enabled non-production targets. Remote restore execution remains disabled.
- `--no-browser` launcher option and single-owner dashboard tab opening.

### Fixed
- Restore progress now exposes real restore subphases instead of one opaque restore stage.
- The dashboard preserves visible backup/restore job state across browser refreshes while the local server remains running and rejects duplicate jobs.

### Security
- Local validation/import and report paths never return dump contents, PATs, database passwords, or credential-bearing URLs.
- Remote restore planning rejects production, read-only, disabled, ambiguous, source-equals-destination, and non-opted-in targets before remote execution can be considered.

### Verification
- 80 automated tests passed with one opt-in Docker integration test skipped in the ordinary suite.
- The disposable synthetic Docker restore was run three times using a pinned official Supabase PostgreSQL image; all runs restored data and protections and cleaned up.

### Added
- Portable headless control-plane backend for MCP-only operation, separate from the Windows desktop control plane.
- Optional Streamable HTTP transport for advanced/remote MCP deployment while preserving stdio as the local default.
- Stable `get_capabilities` / `invoke_capability` live gateway for clients with stale MCP tool metadata.
- Edge Function live capabilities for list/get/deploy through the official Supabase MCP and delete through the documented Management API endpoint.
- Real MCP stdio startup/initialize/tool-discovery regression test.
- Codex integration and Secure MCP Tunnel documentation.
- `query_sql` read-only SQL proxy through the official Supabase MCP.
- `execute_sql` confirmed write-capable SQL proxy for non-read-only targets.
- Automated MCP and local-state regression tests.
- Windows clean-install/startup smoke test in CI.
- Verified installation guide and MCP virtual-environment instructions.
- Supabase CLI v3 compatibility guidance.
- Public repository release surface.
- MCP control-plane documentation.
- Security and contribution documentation.
- GitHub issue and pull-request templates.
- CI and secret-scanning workflows.

### Fixed
- Official Supabase MCP requests now send an explicit `User-Agent`, preventing HTTP 403 responses seen with Python `urllib` defaults.
- MCP state/readiness checks now use the fast local-state endpoint instead of waiting on remote Supabase status checks.
- Setup now enforces Python 3.11+ instead of only checking that Python exists.

### Verification
- Write-capable SQL was verified end-to-end against a real disposable Supabase target using create/insert/select in a temporary table.
- Repository tests remain green after the headless routing and SQL transport changes.

### Security
- Clarified scoped PAT guidance: `Database: Read` permits read-only SQL through the official MCP, while actual SQL writes require `Database: Read-write`; migration permissions remain separate.
- Live capability invocation is server-side whitelisted and preserves explicit confirmation for write-capable operations.
- SQL reads force downstream `read_only=true`; SQL writes require explicit confirmation and are blocked for read-only targets.
- Project PATs used for SQL remain local and are never returned through MCP.
- Documented the no-raw-PAT MCP invariant.
- Documented explicit confirmation for destructive MCP tools.
- Documented ambiguous-resolution safety behavior.

## [0.1.0] - Unreleased

Initial public pre-release.

### Included
- Multi-account Supabase registry.
- Multi-project target management.
- Named Supabase CLI profiles.
- Isolated browser profiles.
- Project-scoped PAT routing.
- Account discovery.
- Local operational dashboard.
- MCP control-plane server.
- Repository-to-project resolution.
- Diagnostics and orphaned-secret detection.

<!-- End of changelog -->

- 3.10.1-dev: Backup & Restore sub-tabs, concise validation, explicit source selection instead of automatically reimporting recent external backups, local pinned Docker image discovery and improved bilingual controls. Remote restore remains disabled.

- 3.10.1-dev UX follow-up: direct history-to-restore selection, Docker image tags with pinned digest, contextual help for source and image selection.

- 3.10.1-dev: derive source PostgreSQL version from dump headers, record it in new manifests, automatically select a local image matching major/minor with latest available build; manual override in advanced settings. Unknown source versions and missing matching images require manual review; no automatic download or compatibility guarantee.

- Restore preflight compares pg_dump COPY column requirements against the isolated database after schema restoration, reporting missing columns before loading rows. This does not reconstruct managed service migrations or validate all SQL forms.

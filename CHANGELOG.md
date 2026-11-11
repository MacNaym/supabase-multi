# Changelog

All notable changes to Supabase Multi will be documented in this file.

The format is based on Keep a Changelog and the project follows Semantic Versioning once stable releases begin.

## [Unreleased]

### Added
- Portable headless control-plane backend for MCP-only operation, separate from the Windows desktop control plane.
- Optional Streamable HTTP transport for advanced/remote MCP deployment while preserving stdio as the local default.
- Stable `get_capabilities` / `invoke_capability` live gateway for clients with stale MCP tool metadata.
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


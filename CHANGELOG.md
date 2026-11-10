# Changelog

All notable changes to Supabase Multi will be documented in this file.

The format is based on Keep a Changelog and the project follows Semantic Versioning once stable releases begin.

## [Unreleased]

### Added
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
- MCP state/readiness checks now use the fast local-state endpoint instead of waiting on remote Supabase status checks.
- Setup now enforces Python 3.11+ instead of only checking that Python exists.

### Security
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


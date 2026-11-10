# Supabase Multi

Local Windows control panel for managing multiple Supabase accounts and projects without constantly switching credentials.

## What it solves

Supabase users working with multiple accounts/projects often need to coordinate:

- different Supabase login identities;
- Supabase CLI named profiles;
- browser sessions;
- account-wide discovery;
- project-scoped Personal Access Tokens;
- MCP targets for AI coding agents;
- local repository → Supabase project routing.

Supabase Multi keeps these concerns separate and gives them one local UI.

## Authentication model

### Account-level
Use either:

- Supabase CLI named profile, or
- an optional Discovery PAT with `Projects (account-wide): Read`.

The Discovery PAT is only for listing/discovering projects visible to an account.

### Project-level
Use a separate scoped PAT per project.

Recommended permissions depend on what your agent needs. A common development profile is:

- Project Settings: Read
- Advisors: Read
- Logs: Read
- API Keys: Read
- Database: Read-write
- Migrations: Read-write
- Edge Functions: Read-write

Supabase recommends scoped PATs for automation and AI agents.

## Security

PAT values are never stored in the registry JSON. They are stored as Windows user environment variables; the registry stores only the environment-variable name.

Browser profiles are local and must never be committed.

The application binds to `127.0.0.1`.

## Current status

The project is an early public release. Core account/project/PAT/CLI/MCP flows are functional and the repository now includes automated unit/regression tests plus a Windows clean-install/startup smoke test. External user feedback is still welcome before declaring a stable 1.0 release.

## Run

Use `start-ui.bat`, then open:

`http://127.0.0.1:8765`

## Languages

The local UI supports English and Italian. English is the default for public distribution.

## Disclaimer

Unofficial community project. Not affiliated with or endorsed by Supabase.


## v3.6.1

- Sidebar labels:
  - Connect account
  - Connect database
  - Authentication
  - Scan account
  - Status
  - Guide
- Output removed from primary navigation.
- Diagnostics / Logs moved inside Status as a collapsible drawer.
- Sidebar uses white text with the same light-blue accent used by the control-panel header.


## v3.6.2

- Diagnostics / Logs now wraps long lines automatically.
- Long command output no longer stretches the page horizontally.


## v3.7.0 RC

- Full EN/IT UI pass.
- English remains the default for public distribution.
- Language switch now covers main navigation, forms, status tables, dialogs, help windows, PAT guide, and dynamic frontend messages.
- Public API/backend errors use English as the stable technical language.


## v3.7.0 RC2

- Translation polish for select menus and environment options.
- Generic dialogs and the Open Project login handoff now use fully opaque cards.
- Darker backdrop added for better focus/readability.


## v3.7.0 RC3

- Fixes false-positive CLI status on newly created accounts.
- `CLI OK` now means:
  1. the account's named CLI profile was explicitly created/managed through Supabase Multi; and
  2. that exact named profile can successfully list Supabase projects.
- New accounts start with CLI disconnected.
- Disconnect clears the managed-profile flag.


## v3.7.0 RC4

- Adds a one-time migration for accounts created before RC3.
- Legacy accounts with a working named Supabase CLI profile are automatically marked as managed.
- Legacy accounts without a working named profile are marked disconnected.
- New accounts still start as CLI disconnected and are never auto-promoted.


## v3.7.0 RC5

- Adds Orphaned secrets cleanup under Status.
- Only Windows user environment variables that look like Supabase PAT/token variables are considered.
- Secret values are never displayed.
- Variables still referenced by any account or project are excluded.
- Delete-one and Clean-all both re-check orphan status server-side before deletion.


## v3.7.0 RC6

- Adds an operational Dashboard as the default landing page.
- KPI cards for database status, accounts, CLI connectivity, project PAT coverage, and orphaned secrets.
- Needs Attention table shows paused/unknown databases, missing PATs, disconnected CLI accounts, incomplete identities, and orphaned secrets.
- Compact database overview shows Supabase state, verification source, PAT status, and MCP target.

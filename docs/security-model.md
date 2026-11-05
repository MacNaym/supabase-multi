# Security Model

Supabase Multi is local-first software.

## Secret storage

Raw PAT values live in Windows User Environment variables.

The registry stores only variable names.

## MCP boundary

Raw PAT values must not cross the MCP boundary.

The MCP layer may report:

```json
{
  "token_env": "SUPABASE_PAT_EXAMPLE",
  "token_present": true
}
```

It must never report the value.

## Browser boundary

PAT authentication is separate from browser login.

Supabase Multi must not inject PAT values into cookies, URLs, or local storage.

## CLI boundary

Each account uses an exact named Supabase CLI profile.

A global/default CLI session must not cause another account to be reported as connected.

## Network exposure

The dashboard binds to `127.0.0.1`.

## Destructive actions

MCP deletion/clear operations require explicit confirmation.

## Ambiguity

Ambiguous project selection is treated as a decision requiring human confirmation, not as permission to guess.

## Release hygiene

Before every public release:

- verify `.gitignore`;
- run secret scanning;
- inspect generated archives;
- verify no personal account/project information is included;
- test installation in a clean environment.

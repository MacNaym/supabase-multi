# Architecture

Supabase Multi has three layers:

```text
Human UI
   │
   ▼
Local control plane
   ▲
   │
Supabase Multi MCP
```

The dashboard and MCP server are two interfaces over the same control-plane state.

## Main components

### Registry

Stores account/project metadata and environment-variable names.

It must not store raw PAT values.

### Local control plane

Responsible for:

- reading and validating registry state;
- checking project status;
- selecting PAT or named-CLI fallback;
- launching isolated browser profiles;
- project discovery;
- MCP target synchronization;
- diagnostics;
- orphaned-secret detection;
- project resolution.

### Human dashboard

Runs locally at `127.0.0.1:8765`.

### Supabase Multi MCP

Exposes routing and administration tools to AI agents.

### Official Supabase MCP

Performs actual project-level Supabase work after Supabase Multi resolves the intended target.

## Resolution

Preferred resolution order is based on explicit evidence:

1. exact target;
2. `project_ref`;
3. repository `.supabase-target.json`;
4. exact/strong name match;
5. constrained account match.

If more than one valid candidate remains, the result is `ambiguous`.

Agents must ask the user which account/project to use.

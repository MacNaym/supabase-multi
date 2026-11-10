# Codex integration

Supabase Multi exposes a standard MCP server over stdio. Codex can consume MCP servers directly, and the same server can also be reached through an OpenAI Secure MCP Tunnel when the process runs on a private machine.

## What has been verified

The repository CI launches `mcp/server.py` as a real stdio MCP process, performs the MCP initialize handshake and lists its tools. This verifies server startup independently of any specific harness.

The project has also been used with Codex through a Secure MCP Tunnel. The tested runtime pattern is:

```text
local Supabase Multi MCP (stdio)
        ↓
OpenAI Secure MCP Tunnel
        ↓
Codex / ChatGPT plugin connection
```

A tunnel runtime profile can be checked with:

```powershell
tunnel-client doctor --profile supabase-multi --explain
```

and kept running with:

```powershell
tunnel-client run --profile supabase-multi
```

Use a restricted runtime credential with only the tunnel permissions required to read/use the configured tunnel. Never put that credential in the repository.

## Local Codex MCP connection

For Codex running on the same Windows machine, the MCP command is:

```text
<INSTALL_PATH>\mcp\.venv\Scripts\python.exe
```

with:

```text
<INSTALL_PATH>\mcp\server.py
```

The MCP process automatically starts the local control plane when a tool needs it.

Codex supports MCP configuration in its CLI/configuration. Because the exact `codex mcp add` flags can change, verify the installed CLI before wiring a local stdio server:

```powershell
codex mcp add --help
codex mcp list
```

After registration, start a **new Codex session** so tool discovery is refreshed. A successful connection should expose at least the routing, administration and SQL tools documented in [mcp.md](mcp.md).

## Startup checks

There are now three separate startup checks:

1. **Python import** — confirms the MCP module and dependencies load.
2. **MCP stdio handshake** — CI launches the server, initializes a real MCP client session and lists tools.
3. **Control-plane smoke test** — CI runs a clean Windows setup, starts `local-ui/server.py`, and verifies `/api/state?local=1`.

The MCP server also performs a runtime readiness check. If `127.0.0.1:8765` is not answering, it starts the control plane itself and waits for the lightweight local-state endpoint before continuing.

## Codex plugin packaging

Current OpenAI plugin packaging supports local stdio MCP servers for desktop-only plugins and remote/tunnel-backed MCP servers for portable/plugin flows.

Supabase Multi does **not** yet ship a public Codex plugin package. The reason is deliberate: a desktop plugin must include or reliably provision its local Python runtime dependencies. The repository currently treats the MCP server itself as the stable integration boundary and tests that boundary directly.

Recommended order before publishing a Codex plugin package:

1. keep the stdio MCP startup test green;
2. test the local connection with the current Codex CLI;
3. test the existing Secure MCP Tunnel path;
4. package the local runtime/dependencies without relying on a globally installed Python package;
5. test installation from a clean Codex/desktop environment.

Until then, use the direct MCP or tunnel route rather than advertising an untested plugin package.

## SQL tools

Supabase Multi adds two SQL-facing tools while keeping target resolution in the control plane:

- `query_sql(target, query)` — always proxies to the official Supabase MCP with `read_only=true`;
- `execute_sql(target, query, confirm=true)` — write-capable path, blocked when the target itself is configured read-only.

The project PAT stays local. Supabase Multi passes it only to the official, project-scoped Supabase MCP endpoint and never returns it to the calling agent.

Agents should resolve the exact target before calling either SQL tool.

# Installation

Supabase Multi currently targets Windows 10/11.

## Requirements

- Python 3.11 or newer
- Brave, Microsoft Edge, or Google Chrome
- an MCP-capable AI client if AI access is desired
- Supabase CLI for named CLI-profile discovery and fallback checks

The dashboard and PAT-based flows can start without the Supabase CLI, but CLI-backed account discovery will be unavailable until the CLI is installed.

For AI agents that need to perform actual database/project work, the official Supabase MCP remains the project-level executor. Supabase Multi stays the local control plane/router and can proxy `query_sql` / `execute_sql` through the official project-scoped MCP after resolving the exact target.

## Clean install

Open PowerShell in the folder where you want the project and run:

```powershell
git clone https://github.com/MacNaym/supabase-multi.git
cd supabase-multi
.\setup.bat
.\start-supabase-multi.bat
```

If you downloaded a release ZIP instead, extract it and run the last two commands from the extracted folder.

`setup.bat`:

1. verifies that Python is at least 3.11;
2. reports whether the Supabase CLI is available;
3. creates `mcp\.venv`;
4. installs the MCP Python dependency inside that virtual environment;
5. creates a local `registry.json` from `registry.example.json` when needed.

`registry.json`, browser profiles, virtual environments and secret values are local state and are excluded from Git.

## Verify the installation

Check the prerequisites:

```powershell
python --version
supabase --version
```

Then start Supabase Multi:

```powershell
.\start-supabase-multi.bat
```

`start-supabase-multi.bat` is readiness-aware: it reuses an already-running control plane instead of starting a duplicate process, and it waits for the local fast-state endpoint before reporting success.

The dashboard should open at:

```text
http://127.0.0.1:8765
```

A lightweight local-state probe is available at:

```text
http://127.0.0.1:8765/api/state?local=1
```

That endpoint intentionally avoids remote Supabase status checks and is used by the MCP server for fast readiness/state reads.

## First configuration

1. Add a Supabase account.
2. Record the account email and login method.
3. Either connect its named Supabase CLI profile or configure an account-wide Discovery PAT.
4. Discover/import projects.
5. Configure a dedicated project-scoped PAT environment variable for each project.
6. Run **MCP Sync**.
7. Run **Doctor**.

Raw PAT values are not stored in `registry.json`.

## Supabase CLI v3

Supabase CLI v3 is supported for the account-scoped operations used by Supabase Multi, including named profiles and `projects list`.

CLI v3 changed the default target behavior of database/deployment commands such as `db push`, `db pull` and related hosted mutations. Supabase Multi does not run those commands as part of its control-plane routing flow. If you run them separately, follow the current Supabase CLI v3 guidance and explicitly choose the intended remote target.

## MCP client

Configure the MCP client to launch:

```text
<INSTALL_PATH>\mcp\.venv\Scripts\python.exe
```

with the argument:

```text
<INSTALL_PATH>\mcp\server.py
```

Example:

```json
{
  "mcpServers": {
    "supabase-multi": {
      "command": "C:\\path\\to\\supabase-multi\\mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\supabase-multi\\mcp\\server.py"]
    }
  }
}
```

The MCP process starts the local control plane automatically when required.

MCP Inspector is only needed for development or troubleshooting.

## Updating

From a Git clone:

```powershell
git pull
.\setup.bat
```

Running `setup.bat` again is safe: it reuses the existing virtual environment and does not replace an existing `registry.json`.

Supabase Multi does not need to run continuously. After updating, start it only when needed with `.\start-supabase-multi.bat` or let your local MCP client launch `mcp\server.py`.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and the main project [README](../README.md).

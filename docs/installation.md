# Installation

## Requirements

- Windows 10/11
- Python 3.11+
- Supabase CLI
- Brave, Edge, or Chrome
- an MCP-capable AI client if AI access is desired

For AI agents that need to perform actual Supabase database/project work, also configure the official Supabase MCP server.

## Install

1. Download or clone Supabase Multi.
2. Run `setup.bat`.
3. Run `start-supabase-multi.bat`.
4. Open `http://127.0.0.1:8765` if the browser does not open automatically.
5. Add an account.
6. Connect its named Supabase CLI profile.
7. Discover/import projects.
8. Configure project PAT environment variables.
9. Run MCP Sync.
10. Run Doctor.

## MCP client

Point your MCP client to:

```text
<INSTALL_PATH>\mcp\.venv\Scripts\python.exe
```

with:

```text
<INSTALL_PATH>\mcp\server.py
```

MCP Inspector is only needed for development or troubleshooting.

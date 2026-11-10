# Tests

Supabase Multi uses pytest for focused regression tests and GitHub Actions for a Windows installation smoke test.

Current coverage focuses on the contracts most likely to cause unsafe or confusing failures:

- MCP state reads must use `/api/state?local=1`;
- local-state construction must not perform remote Supabase/CLI checks;
- MCP public views must not expose raw secret fields;
- destructive MCP helpers must require explicit confirmation;
- a clean checkout must run `setup.bat`, create the MCP virtual environment and local registry, start the control plane, and answer the fast local-state endpoint.

Run locally from the repository root:

```powershell
.\mcp\.venv\Scripts\python.exe -m pip install pytest
.\mcp\.venv\Scripts\python.exe -m pytest -q
```

Tests must never require real PAT values or a real Supabase project.

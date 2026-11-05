# Contributing to Supabase Multi

Thanks for helping improve Supabase Multi.

## Before opening a pull request

1. Search existing issues and pull requests.
2. Keep the change focused.
3. Do not include personal account data, project refs, PAT values, browser profiles, or local paths.
4. Add or update tests for behavior changes.
5. Update documentation when changing user-facing behavior.
6. Run the local checks described below.

## Development setup

From the repository root:

```powershell
python -m venv .\mcp\.venv
.\mcp\.venv\Scripts\python.exe -m pip install --upgrade pip
.\mcp\.venv\Scripts\python.exe -m pip install -r .\mcp\requirements.txt
```

For MCP development:

```powershell
cd .\mcp
.\.venv\Scripts\mcp.exe dev server.py
```

MCP Inspector is a development and troubleshooting tool. It is not part of the normal end-user flow.

## Pull request expectations

A pull request should explain:

- what problem it solves;
- what changed;
- how it was tested;
- whether it affects security, routing, secrets, or destructive actions;
- whether documentation changed.

## Project rules

- Never expose raw PAT values.
- Never commit `registry.json`.
- Never guess a Supabase target.
- If resolution is ambiguous, return candidates and require the agent to ask the user.
- Keep UI and MCP backed by the same control-plane source of truth.
- Keep destructive actions confirmation-gated.
- Prefer small, reviewable changes.

## Commit hygiene

Use concise, descriptive commits. Examples:

```text
fix: verify scoped PAT using project endpoint
feat: add orphaned secret cleanup
docs: clarify official Supabase MCP dependency
test: cover ambiguous project resolution
```

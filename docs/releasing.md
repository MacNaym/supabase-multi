# Releasing

## Pre-release gate

Before creating a release:

1. run tests;
2. verify MCP import;
3. verify tool discovery;
4. test `get_dashboard`;
5. test resolved/ambiguous/not-found routing;
6. test PAT and CLI fallback behavior;
7. test `query_sql` against a disposable/non-production target;
8. when SQL transport changed, test `execute_sql(..., confirm=true)` end-to-end against a disposable target and verify the target read-only gate;
9. test destructive confirmation gates;
10. verify the MCP tool count and live capability registry;
11. run secret scanning;
12. inspect `git status`;
13. test a clean install from the release archive.

## Versioning

Use Semantic Versioning once the public API stabilizes.

Pre-release examples:

```text
0.1.0
0.2.0
0.2.1
```

## Release artifact

A release should publish:

```text
supabase-multi-vX.Y.Z.zip
SHA256SUMS.txt
```

Do not include:

- `registry.json`;
- `.env*`;
- browser profiles;
- OAuth session data;
- `.venv`;
- personal paths;
- real account/project data.

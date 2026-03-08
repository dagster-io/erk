# Fix: erk-mcp missing from uv workspace sources

## Context

Every time a codespace connection is established, `uv sync` runs (via `.erk/bin/activate.sh`) and uninstalls 47 packages. These are all transitive dependencies of `erk-mcp` (fastmcp, mcp, starlette, uvicorn, etc.). The root cause is that `erk-mcp` is not declared in `[tool.uv.sources]` in the root `pyproject.toml`, so uv doesn't recognize it as a local workspace package and strips its dependencies.

## Change

**File:** `pyproject.toml` (line 5)

Add `erk-mcp = { workspace = true }` to `[tool.uv.sources]`:

```toml
[tool.uv.sources]
erk-dev = { workspace = true }
erk-mcp = { workspace = true }
erk-shared = { workspace = true }
erk-statusline = { workspace = true }
```

## Verification

1. Run `uv sync` — should not uninstall any packages
2. Run `uv sync` again — should be a no-op ("Resolved X packages in Yms" with no installs/uninstalls)

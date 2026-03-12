# Plan: Make uv workspace resilient to stray directories

## Context

The `pyproject.toml` uses `members = ["packages/*"]` glob for workspace members. When a worktree has a stray directory under `packages/` without a `pyproject.toml` (e.g., `packages/erkbot` lingering after branch operations), `uv sync` fails with:

```
error: Workspace member `.../packages/erkbot` is missing a `pyproject.toml`
```

This happens because git doesn't always clean up empty directories when switching/rebasing branches. In erk's worktree-heavy workflow, this is a recurring hazard.

## Change

In `pyproject.toml`, replace the glob with explicit members:

```toml
# Before
[tool.uv.workspace]
members = ["packages/*"]

# After
[tool.uv.workspace]
members = [
    "packages/erk-dev",
    "packages/erk-mcp",
    "packages/erk-shared",
    "packages/erk-statusline",
]
```

### Files to modify
- `pyproject.toml` (line 2)

## Tradeoffs

- **Pro**: Immune to stray directories breaking `uv sync`
- **Con**: Must update `pyproject.toml` when adding/removing workspace packages (rare, and you'd be editing it anyway to add the dependency)

## Verification

1. Run `uv sync` to confirm it still works
2. Create a stray directory `packages/fake-pkg/` (no pyproject.toml) and verify `uv sync` still succeeds
3. Clean up `packages/fake-pkg/`

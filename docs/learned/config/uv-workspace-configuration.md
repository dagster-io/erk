---
title: UV Workspace Configuration
read_when:
  - "adding a new workspace package to erk"
  - "debugging uv sync failures related to missing pyproject.toml"
  - "understanding why explicit members are preferred over globs"
tripwires:
  - action: "adding a new workspace package without updating pyproject.toml members list"
    warning: "The workspace uses explicit members, not globs. New packages added to packages/ are NOT automatically discovered. Add the package path to [tool.uv.workspace] members in pyproject.toml or uv sync will fail."
---

# UV Workspace Configuration

Erk uses an explicit member list in `[tool.uv.workspace]` rather than a glob pattern.

## Configuration

**Source**: Root `pyproject.toml` (lines 1-8)

```toml
[tool.uv.workspace]
members = [
    "packages/erk-dev",
    "packages/erk-mcp",
    "packages/erk-shared",
    "packages/erk-slots",
    "packages/erk-statusline",
]
```

## Why Explicit Members (Not Globs)

A glob like `packages/*` would automatically discover all subdirectories. The explicit list is intentional:

**Problem with globs**: If any stray directory in `packages/` lacks a `pyproject.toml` (e.g., a temp directory, a checkout artifact, or a partial extraction), `uv sync` will fail with an error about a missing `pyproject.toml`.

**Benefit of explicit list**: Only known, valid packages are included. Stray directories don't break the workspace.

**Trade-off**: Developers must manually add new packages to the members list. This is a minor friction compared to the resilience gained.

## Adding a New Workspace Package

When creating a new package under `packages/`:

1. Create the package directory with a valid `pyproject.toml`
2. Add the path to `[tool.uv.workspace]` members in the root `pyproject.toml`
3. Add a `[tool.uv.sources]` entry if needed
4. Run `uv sync` to verify the workspace is valid

Example for a new package `erk-newpkg`:

```toml
[tool.uv.workspace]
members = [
    "packages/erk-dev",
    "packages/erk-mcp",
    "packages/erk-shared",
    "packages/erk-slots",
    "packages/erk-statusline",
    "packages/erk-newpkg",  # ← add here
]

[tool.uv.sources]
erk-newpkg = { workspace = true }  # ← add here if consumed by root package
```

## Related Documentation

- [Configuration Layers](../configuration/config-layers.md) — Erk config file structure

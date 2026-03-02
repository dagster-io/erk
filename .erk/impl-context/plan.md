# Loosen Pydantic Version Constraint to >=2.0

## Context

Pydantic is currently pinned to `>=2.10` across the project. The user wants to allow any Pydantic v2 release.

## Changes

1. **`pyproject.toml:25`** — Change `"pydantic>=2.10"` to `"pydantic>=2.0"`
2. **`packages/erkbot/pyproject.toml:15`** — Change `"pydantic>=2.10"` to `"pydantic>=2.0"`
3. **`packages/erkbot/pyproject.toml:16`** — Change `"pydantic-settings>=2.4.0"` to `"pydantic-settings>=2.0"`

## Verification

- Run `uv sync` to confirm dependency resolution works
- Run `uv lock --check` or inspect `uv.lock` for the resolved version

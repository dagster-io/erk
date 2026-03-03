# Plan: Create erk-mcp Server

## Context

Build an MCP server so erk's capabilities can be exposed to any MCP client — starting with Claude Code locally. Prototype validates the architecture with 3 tools: `plan_list`, `plan_view`, and `one_shot`.

## Package structure

```
packages/erk-mcp/
├── pyproject.toml
└── src/
    └── erk_mcp/
        ├── __init__.py
        ├── __main__.py
        └── server.py
```

## `pyproject.toml`

```toml
[project]
name = "erk-mcp"
version = "0.1.0"
description = "FastMCP server exposing erk capabilities as MCP tools"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
]

[project.scripts]
erk-mcp = "erk_mcp.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/erk_mcp"]
```

No dependency on `erk` or `erk-shared` — shells out to the `erk` CLI.

## `server.py` — 3 tools

Shared helper `_run_erk(args)` uses `subprocess.run(check=False)` with returncode checking.

**`plan_list`** — Calls `erk exec dash-data`, returns structured JSON. Optional `state` filter.

**`plan_view`** — Calls `erk exec get-plan-info <plan_id> --include-body`, returns plan metadata + body.

**`one_shot`** — Calls `erk one-shot "<prompt>"`, parses PR/run URLs from output. Returns after dispatch (~10-30s).

## Config changes

- Add `"erk_mcp"` to `known-first-party` in `pyproject.toml` `[tool.ruff.lint.isort]`
- Create `.mcp.json` at repo root for Claude Code integration

## Verification

1. `uv sync` — workspace resolves with erk-mcp
2. Start new Claude Code session — confirm erk MCP server appears with 3 tools
3. Test `plan_list` and `plan_view` via Claude Code

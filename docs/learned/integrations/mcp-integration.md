---
title: Erk MCP Integration
read_when:
  - "adding new MCP tools to erk"
  - "configuring erk as an MCP server for Claude"
  - "understanding the erk-mcp package structure"
  - "debugging MCP tool calls from external clients"
---

# Erk MCP Integration

Erk exposes its capabilities as an MCP (Model Context Protocol) server via the `erk-mcp` package. This allows external MCP clients (e.g., Claude Desktop, other AI tools) to invoke erk operations.

## Package Structure

<!-- Source: packages/erk-mcp/src/erk_mcp/server.py -->

```
packages/erk-mcp/
├── pyproject.toml           # Package definition, depends on fastmcp>=2.0
└── src/erk_mcp/
    ├── __init__.py
    ├── __main__.py          # Entry point: parses --transport/--host/--port, calls create_mcp().run()
    └── server.py            # Tool definitions and _run_erk() wrapper
```

The package depends on [FastMCP](https://github.com/jlowin/fastmcp) (`fastmcp>=2.0`) and is a thin wrapper that delegates to the `erk` CLI.

## CLI Wrappers

<!-- Source: packages/erk-mcp/src/erk_mcp/server.py -->

Two internal wrappers in `server.py` delegate to the erk CLI:

- **Standard wrapper** — Runs `erk <args>`, raises `RuntimeError` on non-zero exit. Used by hand-written tools (`plan_list`, `plan_view`).
- **JSON wrapper** — Runs `erk <command> --json`, pipes params as JSON stdin. Does NOT raise on non-zero exit — `--json` guarantees structured error output flows through to the agent. Used by auto-discovered MCP tools.

## MCP Tools

Three tools are registered:

| Tool        | Delegates To             | Purpose                                       |
| ----------- | ------------------------ | --------------------------------------------- |
| `plan_list` | `erk exec dash-data`     | List plans with status, labels, metadata      |
| `plan_view` | `erk exec get-plan-info` | View a specific plan's metadata and body      |
| `one_shot`  | `erk one-shot --json`    | Submit a task for autonomous remote execution |

### `plan_list`

<!-- Source: packages/erk-mcp/src/erk_mcp/server.py -->

Returns structured JSON from the erk dashboard. Optional state filter (`"open"` or `"closed"`).

### `plan_view`

<!-- Source: packages/erk-mcp/src/erk_mcp/server.py -->

Returns plan title, state, labels, and full markdown body for a given plan ID.

### `one_shot` (auto-discovered via `@mcp_exposed`)

Dispatches a task for fully autonomous execution via `erk one-shot --json`. Returns structured JSON indicating success or failure. On success, includes the created PR reference and CI run details. With `dry_run`: preview without executing.

Parameters are auto-derived from Click parameters — no separate schema class needed.

## Auto-Discovery from Click Command Tree

<!-- Source: packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py, packages/erk-mcp/src/erk_mcp/server.py -->

CLI commands decorated with both `@json_command` and `@mcp_exposed` are automatically discovered and registered as MCP tools. One source of truth (Click parameters), two interfaces (CLI and MCP).

### Adding a new MCP tool

1. Add `@mcp_exposed(name="tool_name", description="...")` above `@json_command` on the Click command
2. Done — the server walks the Click tree at startup and registers it automatically

<!-- Source: src/erk/cli/commands/one_shot.py, one_shot command decorator stack -->

See the `one_shot` command decorator stack in `src/erk/cli/commands/one_shot.py` for the canonical example of `@mcp_exposed` / `@json_command` / `@click.command` layering.

### How it works

- The `@mcp_exposed` decorator attaches MCP metadata (name, description) to the Click command
- At startup, the server walks the Click tree to find all decorated commands
- Each command's Click parameters are automatically converted to a JSON Schema
- Each discovered command is wrapped as a FastMCP `Tool`

At runtime, each tool filters out unset parameters before piping the remaining values as JSON to the CLI.

### Parity tests

<!-- Source: tests/unit/cli/ -->

Parity tests enforce:

- Every `@mcp_exposed` command is registered as an MCP tool
- Each tool's schema matches the Click-derived schema
- No orphaned tools exist without a corresponding `@mcp_exposed` command

## Configuration

The MCP server is configured in `.mcp.json` at the repository root:

```json
{
  "mcpServers": {
    "erk": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--package", "erk-mcp", "erk-mcp"]
    }
  }
}
```

This uses `uv run` to execute the `erk-mcp` entry point via stdio IPC (the `"type": "stdio"` in `.mcp.json` describes the Claude-to-server protocol). Internally, `__main__.py` defaults to `streamable-http` transport when no `--transport` arg is given.

## Makefile Targets

<!-- Source: Makefile, mcp/mcp-dev/test-erk-mcp targets -->

See the `mcp`, `mcp-dev`, and `test-erk-mcp` targets in `Makefile` for current definitions.

- `make mcp` — Run the MCP server (production mode, stdio transport)
- `make mcp-dev` — Run with FastMCP inspector for interactive testing
- `make test-erk-mcp` — Run the MCP package tests

## CI Job

<!-- Source: .github/workflows/ci.yml, erk-mcp-tests job -->

The `erk-mcp-tests` job runs in Tier 3 (parallel validation), depending on `check-submission` and `fix-formatting`. See the `erk-mcp-tests` job in `.github/workflows/ci.yml` for the current definition.

See [CI Job Ordering Strategy](../ci/job-ordering-strategy.md) for the full Tier 3 validation job list.

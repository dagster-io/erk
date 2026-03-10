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
- **JSON wrapper** — Runs `erk json <command>`, pipes params as JSON stdin. Does NOT raise on non-zero exit — machine commands guarantee structured error output flows through to the agent. Used by auto-discovered MCP tools.

## Auto-Discovery from Click Command Tree

<!-- Source: packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py, packages/erk-mcp/src/erk_mcp/server.py -->

CLI commands decorated with `@machine_command` are automatically discovered and registered as MCP tools. The `@machine_command` decorator stores `MachineCommandMeta` on the command, and `discover_machine_commands()` walks the Click tree to find them.

### Adding a new MCP tool

1. Create a core operation (`*_operation.py`) with request/result dataclasses
2. Create a machine command under `src/erk/cli/commands/json/` with `@machine_command`
3. Register in the json group's `__init__.py`
4. Done — the server discovers it automatically at startup

### How it works

- `@machine_command` stores `MachineCommandMeta` (name, description, request_type, result_types) on the command
- At startup, `discover_machine_commands()` walks the Click tree for `_machine_command_meta` attributes
- Each command's input schema is derived from the request dataclass fields (not Click parameters)
- Each discovered command is wrapped as a `MachineCommandTool` (FastMCP `Tool`)

At runtime, each tool pipes parameters as JSON stdin to `erk json <command-path>`.

### Parity tests

<!-- Source: tests/unit/cli/test_mcp_cli_sync.py -->

Parity tests enforce:

- Every `@machine_command` command is registered as an MCP tool
- Each tool's schema matches the request-derived schema
- No orphaned tools exist without a corresponding `@machine_command` command

## MCP Tools

Hand-written tools:

| Tool        | Delegates To             | Purpose                                  |
| ----------- | ------------------------ | ---------------------------------------- |
| `plan_list` | `erk exec dash-data`     | List plans with status, labels, metadata |
| `plan_view` | `erk exec get-plan-info` | View a specific plan's metadata and body |

Auto-discovered tools (via `@machine_command`):

| Tool       | CLI Path            | Purpose                                       |
| ---------- | ------------------- | --------------------------------------------- |
| `one_shot` | `erk json one-shot` | Submit a task for autonomous remote execution |
| `pr_list`  | `erk json pr list`  | List plans filtered by state and labels       |
| `pr_view`  | `erk json pr view`  | View a specific plan's details                |

## Configuration

The repository does not ship a default `.mcp.json`. To use the MCP server locally, create a `.mcp.json` in the project root (it is gitignored) or add the server to your user-level Claude Code settings:

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

This uses `uv run` to execute the `erk-mcp` entry point via stdio IPC. Internally, `__main__.py` defaults to `streamable-http` transport when no `--transport` arg is given.

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

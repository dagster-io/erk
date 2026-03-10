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
    └── server.py            # Tool definitions and _run_erk_json() wrapper
```

The package depends on [FastMCP](https://github.com/jlowin/fastmcp) (`fastmcp>=2.0`) and is a thin wrapper that delegates to the `erk` CLI.

## CLI Wrappers

<!-- Source: packages/erk-mcp/src/erk_mcp/server.py -->

The MCP server uses a JSON wrapper that runs `erk json <command>` and pipes params as JSON stdin. It does NOT raise on non-zero exit — machine commands guarantee structured error output flows through to the agent.

## MCP Tools

Tools are auto-discovered from the `erk json` command tree:

| Tool       | Delegates To        | Purpose                                       |
| ---------- | ------------------- | --------------------------------------------- |
| `one_shot` | `erk json one-shot` | Submit a task for autonomous remote execution |
| `pr_list`  | `erk json pr list`  | List plans with status, labels, metadata      |
| `pr_view`  | `erk json pr view`  | View a specific plan's metadata and body      |

### Auto-Discovery from Click Command Tree

<!-- Source: packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py, packages/erk-mcp/src/erk_mcp/server.py -->

CLI commands decorated with both `@machine_command` and `@mcp_exposed` are automatically discovered and registered as MCP tools. One source of truth (request dataclass), two interfaces (CLI and MCP).

### Adding a new MCP tool

1. Create an operation file with `Request` and `Result` dataclasses
2. Create a machine adapter in the command's own subpackage (e.g., `src/erk/cli/commands/foo/json_cli.py`) with `@mcp_exposed` + `@machine_command` + `@click.command`
3. Register it in the `json_group`
4. Done — the server walks the Click tree at startup and registers it automatically

See `src/erk/cli/commands/one_shot/json_cli.py` for the canonical example.

### How it works

- The `@mcp_exposed` decorator attaches MCP metadata (name, description) to the Click command
- The `@machine_command` decorator attaches machine command metadata (request_type, output_types) to the Click command
- At startup, the server walks the Click tree to find all commands with both decorators applied
- Each command's request type is converted to a JSON Schema via `request_schema()`
- Each discovered command is wrapped as a FastMCP `Tool` (`MachineCommandTool`)

At runtime, each tool pipes input parameters as JSON stdin to `erk json <command>`.

### Parity tests

<!-- Source: tests/unit/cli/ -->

Parity tests enforce:

- Every `@mcp_exposed` command is registered as an MCP tool
- Each tool's schema matches the request-derived schema
- No orphaned tools exist without a corresponding `@mcp_exposed` command

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

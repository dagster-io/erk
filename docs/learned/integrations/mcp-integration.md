---
title: Erk MCP Integration
read_when:
  - "adding new MCP tools to erk"
  - "configuring erk as an MCP server for Claude"
  - "understanding the erk-mcp package structure"
  - "debugging MCP tool calls from external clients"
---

# Erk MCP Integration

Erk exposes MCP tools through the `erk-mcp` package. The server is intentionally thin: it discovers machine commands from the CLI tree and shells out to `erk json ...`.

## Package Structure

```
packages/erk-mcp/
├── pyproject.toml
└── src/erk_mcp/
    ├── __init__.py
    ├── __main__.py
    └── server.py
```

`server.py` is the important file. It discovers MCP-exposed commands, builds FastMCP tools, and delegates execution back to the Erk CLI.

## Machine-Command Wrapper

The server uses `_run_erk_json()` to execute machine commands:

- subprocess command: `erk json ...`
- request transport: JSON piped on stdin
- response transport: structured JSON read from stdout

It does not parse human-readable CLI output.

## Tool Discovery

MCP tools are auto-discovered from commands decorated with `@mcp_exposed`.

Current pattern:

```python
@mcp_exposed(name="one_shot", description="...")
@machine_command(...)
@click.command("one-shot")
def json_one_shot(...):
    ...
```

`discover_mcp_commands()` walks the Click tree, returns the command plus its CLI path, and the server registers a FastMCP tool for each discovered machine command.

The tool schema comes from `command_input_schema(cmd)`, which reads the machine command request contract.

## Current Tool Shape

With the machine-command split, tools now map to explicit machine paths such as:

- `("json", "one-shot")`
- `("json", "pr", "list")`
- `("json", "pr", "view")`

That path is what the MCP server executes.

## Adding a New MCP Tool

1. create or update the shared operation layer
2. add the machine command under `src/erk/cli/commands/json/`
3. decorate that machine command with `@mcp_exposed`
4. ensure the command has stable request/result contracts for schema generation
5. add parity tests for discovery and schema

No extra MCP registration code is needed unless the server architecture changes.

## Parity Tests

Important tests live in:

- `tests/unit/cli/test_mcp_cli_sync.py`
- `packages/erk-mcp/tests/test_server.py`

These verify:

- every `@mcp_exposed` command is discoverable
- tool schemas match command-derived schemas
- MCP executes the `erk json ...` path, not the human command

## Local Configuration

The repo does not ship a default `.mcp.json`. A local config typically uses `uv run`:

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

## Operational Rule

If an agent-facing CLI feature should be callable from MCP, implement the machine command first. MCP is downstream of the `erk json ...` tree.

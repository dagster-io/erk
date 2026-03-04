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
    ├── __main__.py          # Entry point: calls create_mcp().run()
    └── server.py            # Tool definitions and _run_erk() wrapper
```

The package depends on [FastMCP](https://github.com/jlowin/fastmcp) (`fastmcp>=2.0`) and is a thin wrapper that delegates to the `erk` CLI.

## The `_run_erk()` Wrapper

All tools delegate to the erk CLI via `_run_erk()`:

```python
def _run_erk(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run an erk CLI command and return the result."""
    result = subprocess.run(
        ["erk", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"erk {' '.join(args)} failed (exit {result.returncode}): {stderr}")
    return result
```

Non-zero exit codes raise `RuntimeError` with the stderr message. MCP clients receive this as a tool error.

## MCP Tools

Three tools are registered:

| Tool        | Delegates To             | Purpose                                       |
| ----------- | ------------------------ | --------------------------------------------- |
| `plan_list` | `erk exec dash-data`     | List plans with status, labels, metadata      |
| `plan_view` | `erk exec get-plan-info` | View a specific plan's metadata and body      |
| `one_shot`  | `erk one-shot <prompt>`  | Submit a task for autonomous remote execution |

### `plan_list(state: str | None = None) -> str`

Returns structured JSON from the erk dashboard. The optional `state` parameter filters by `"open"` or `"closed"`.

### `plan_view(plan_id: int) -> str`

Returns plan title, state, labels, and full markdown body for the given plan ID. Uses `--include-body` flag.

### `one_shot(prompt: str) -> str`

Dispatches a task for fully autonomous execution: creates a branch, draft PR, and triggers a GitHub Actions workflow. Returns after dispatch (~10-30s) with PR and workflow run URLs.

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

This uses `uv run` to execute the `erk-mcp` entry point, which calls `create_mcp().run()` (stdio transport).

## Makefile Targets

```makefile
mcp:
    uv run --package erk-mcp erk-mcp

mcp-dev:
    uv run --package erk-mcp fastmcp dev inspector packages/erk-mcp/src/erk_mcp/server.py:mcp

test-erk-mcp:
    cd packages/erk-mcp && uv run pytest tests/ -x -q
```

- `make mcp` — Run the MCP server (production mode, stdio transport)
- `make mcp-dev` — Run with FastMCP inspector for interactive testing
- `make test-erk-mcp` — Run the MCP package tests

## CI Job

The `erk-mcp-tests` job runs in Tier 3 (parallel validation), depending on `check-submission` and `fix-formatting`:

```yaml
erk-mcp-tests:
  needs: [check-submission, fix-formatting]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: ./.github/actions/setup-python-uv
    - name: Run erk-mcp tests
      run: make test-erk-mcp
```

See [CI Job Ordering Strategy](../ci/job-ordering-strategy.md) for the full Tier 3 validation job list.

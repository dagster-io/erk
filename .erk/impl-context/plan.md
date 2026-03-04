# Plan: erk-mcp HTTP Transport Support

## Context

The erk-mcp server currently only supports stdio transport (`mcp.run()` with no args). The user wants to run it over HTTP (streamable-http), similar to how `compass-dev mcp test-server --port 9000` works in the compass project. HTTP transport is preferable for persistent server setups and Claude Code integration via URL.

**Reference:** `compass-dev mcp test-server` uses `FastMCP("name", host="0.0.0.0", port=port)` + `server.run(transport="streamable-http")`.

## Current State

```python
# packages/erk-mcp/src/erk_mcp/__main__.py  (current)
from erk_mcp.server import mcp

def main() -> None:
    mcp.run()  # always stdio
```

```python
# packages/erk-mcp/src/erk_mcp/server.py  (current)
from fastmcp import FastMCP

mcp = FastMCP("erk")

@mcp.tool()
def plan_list(...): ...

@mcp.tool()
def plan_view(...): ...

@mcp.tool()
def one_shot(...): ...
```

## Implementation

### 1. Refactor `server.py` — `create_mcp()` factory

Move from a module-level `mcp` global (causes import-time side effects, hard to test) to a factory function with a lazy import. This matches the compass pattern and makes the tools testable independently.

```python
# packages/erk-mcp/src/erk_mcp/server.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

DEFAULT_MCP_NAME = "erk"

def _run_erk(args: list[str]) -> subprocess.CompletedProcess[str]:
    ...  # unchanged

def plan_list(state: str | None = None) -> str:
    ...  # unchanged, no decorator

def plan_view(plan_id: int) -> str:
    ...  # unchanged, no decorator

def one_shot(prompt: str) -> str:
    ...  # unchanged, no decorator

def create_mcp() -> "FastMCP":
    from fastmcp import FastMCP
    mcp = FastMCP(DEFAULT_MCP_NAME)
    mcp.tool()(plan_list)
    mcp.tool()(plan_view)
    mcp.tool()(one_shot)
    return mcp
```

### 2. Rewrite `__main__.py` — CLI with transport/host/port

Add `--transport` (streamable-http|stdio), `--host`, `--port`, and env var support. Default to `streamable-http`. Print the URL on startup for HTTP transport.

```python
# packages/erk-mcp/src/erk_mcp/__main__.py
import argparse, os
from erk_mcp.server import create_mcp

def _parse_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)

def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Erk MCP server.")
    parser.add_argument("--host", default=os.getenv("ERK_MCP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=_parse_int_env("ERK_MCP_PORT", 9000))
    parser.add_argument("--transport", choices=["streamable-http", "stdio"],
                        default="streamable-http")
    return parser.parse_args(argv)

def main() -> None:
    args = _parse_args()
    mcp = create_mcp()
    if args.transport == "stdio":
        mcp.run()
    else:
        print(f"Starting erk MCP server on http://{args.host}:{args.port}/mcp")
        mcp.run(transport=args.transport, host=args.host, port=args.port)
```

### 3. Add tests

**`packages/erk-mcp/tests/test_main.py`** — test arg parsing and startup:
- Default args: streamable-http, 0.0.0.0, 9000
- Env var overrides (`ERK_MCP_HOST`, `ERK_MCP_PORT`)
- CLI flag overrides (`--port`, `--host`, `--transport`)
- HTTP startup calls `mcp.run(transport=..., host=..., port=...)` and prints URL
- Stdio startup calls `mcp.run()` with no args, no print

### 4. Register erk-mcp in Claude Code settings

Add to **`~/.claude/settings.json`** under `mcpServers` so Claude Code connects to the running server:

```json
"mcpServers": {
  "erk": {
    "type": "http",
    "url": "http://localhost:9000/mcp"
  }
}
```

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-mcp/src/erk_mcp/server.py` | Add `create_mcp()` factory, remove module-level global, remove `@mcp.tool()` decorators |
| `packages/erk-mcp/src/erk_mcp/__main__.py` | Full rewrite: CLI args, transport selection, startup print |
| `packages/erk-mcp/tests/test_main.py` | New file: arg parsing + startup tests |
| `~/.claude/settings.json` | Add `mcpServers.erk` HTTP entry |

## Verification

1. Run tests: `cd packages/erk-mcp && uv run pytest tests/ -v`
2. Start server: `uv run erk-mcp` → should print `Starting erk MCP server on http://0.0.0.0:9000/mcp`
3. Custom port: `uv run erk-mcp --port 8080` → prints `...http://0.0.0.0:8080/mcp`
4. Stdio regression: `uv run erk-mcp --transport stdio` → starts silently with stdio transport
5. New Claude Code session → erk MCP tools appear (plan_list, plan_view, one_shot)

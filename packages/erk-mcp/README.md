# erk-mcp

FastMCP server exposing erk capabilities as MCP tools.

## Running the server

```bash
uv run erk-mcp
# Starting erk MCP server on http://0.0.0.0:9000/mcp
```

### Options

| Flag          | Env var        | Default           | Description                             |
| ------------- | -------------- | ----------------- | --------------------------------------- |
| `--transport` | —              | `streamable-http` | Transport: `streamable-http` or `stdio` |
| `--host`      | `ERK_MCP_HOST` | `0.0.0.0`         | Bind address                            |
| `--port`      | —              | `9000`            | Port                                    |

```bash
uv run erk-mcp --port 8080
uv run erk-mcp --host 127.0.0.1 --port 8080
uv run erk-mcp --transport stdio
```

## Claude Code integration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "erk": {
      "type": "http",
      "url": "http://localhost:9000/mcp"
    }
  }
}
```

Then start the server before launching Claude Code. The `pr_list`, `pr_view`, and `one_shot` tools will be available in your session.

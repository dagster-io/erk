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

## GitHub OAuth

`erk-mcp` can expose MCP-compatible OAuth endpoints backed by GitHub. Set these
environment variables before starting the HTTP server:

```bash
export ERK_MCP_GITHUB_OAUTH_CLIENT_ID=...
export ERK_MCP_GITHUB_OAUTH_CLIENT_SECRET=...
export ERK_MCP_PUBLIC_URL=https://your-public-erk-host.example.com
```

Optional:

```bash
export ERK_MCP_GITHUB_OAUTH_SCOPES=repo
```

When configured, `erk-mcp` exposes OAuth discovery at:

```text
https://your-public-erk-host.example.com/.well-known/oauth-authorization-server
```

For clients that probe protected-resource metadata at the root, `erk-mcp` also
serves:

```text
https://your-public-erk-host.example.com/.well-known/oauth-protected-resource
```

At startup, `erk-mcp` prints both OAuth URLs when auth is enabled. If the required
OAuth environment variables are missing, HTTP startup now fails closed instead of
serving without authentication. Use `uv run erk-mcp --transport stdio` if you do
not want to configure HTTP auth.

and uses GitHub OAuth with callback:

```text
https://your-public-erk-host.example.com/auth/callback
```

The MCP client receives a bearer token from FastMCP, and `erk-mcp` resolves that
back to the authenticated upstream GitHub token before invoking `erk`.
Direct `Authorization: Bearer <github-token>` passthrough is not supported.

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

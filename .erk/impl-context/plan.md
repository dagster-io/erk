# Plan: Per-User GitHub Attribution for erk-mcp (dagster-compass side)

## Context

erk-mcp now reads `Authorization: Bearer <token>` on each MCP request and injects it as `GH_TOKEN`
into the `erk` subprocess. This means Compass only needs to send the user's GitHub OAuth token as
the Bearer token — no other changes to erk-mcp are required.

The erk-mcp PR (#TODO — link when merged) contains the middleware and ContextVar plumbing.
This plan wires the Compass side: storing user-scoped tokens, loading them per-request,
and surfacing an auth-required prompt for users who haven't connected their GitHub account.

The `mcp_server_auth` table already has `scope IN ('organization', 'user')` and `org_user_id` FK
(see `schema_changes.py`). The application layer just needs to activate the per-user path.

---

## Phase 1: Storage Layer

### `packages/csbot/src/csbot/slackbot/storage/interface.py`

Add user-scoped save method alongside the existing org-scoped one:

```python
async def save_mcp_server_oauth_for_user(
    self,
    mcp_server_id: int,
    organization_id: int,
    org_user_id: int,
    access_token: str,
    refresh_token: str | None,
    token_expires_at: datetime | None,
) -> None: ...
```

### `packages/csbot/src/csbot/slackbot/storage/postgresql.py`

Implement `save_mcp_server_oauth_for_user` with `scope='user', org_user_id=<id>` using an upsert
on the `idx_mcp_server_auth_user` index.

Update `_load_mcp_servers()` to accept an optional `org_user_id` parameter. Use a LEFT JOIN to load
both the org-scoped and user-scoped tokens, preferring the user-scoped token when available:

```sql
LEFT JOIN mcp_server_auth ma_org
    ON ms.id = ma_org.mcp_server_id AND ma_org.scope = 'organization'
LEFT JOIN mcp_server_auth ma_user
    ON ms.id = ma_user.mcp_server_id
    AND ma_user.scope = 'user' AND ma_user.org_user_id = %(org_user_id)s
-- COALESCE: prefer user-scoped token over org-scoped
COALESCE(ma_user.encrypted_access_token, ma_org.encrypted_access_token) AS encrypted_access_token,
COALESCE(ma_user.encrypted_refresh_token, ma_org.encrypted_refresh_token) AS encrypted_refresh_token,
COALESCE(ma_user.token_expires_at, ma_org.token_expires_at) AS token_expires_at,
```

When `org_user_id=None`, the `ma_user` join matches nothing and COALESCE falls back to
the org-scoped token — preserving existing bot-fallback behavior.

Also add a boolean `has_user_token` column (derived from `ma_user.id IS NOT NULL`) so callers
can detect whether a user has connected their account.

---

## Phase 2: OAuth Flow — Capture User Identity

### `packages/csbot/src/csbot/slackbot/webapp/mcp_oauth.py`

**`mcp_oauth_start`**: Require user context (available via `ViewerContext`/session cookie).
Pass `org_user_id` through the OAuth state parameter so the callback knows which user to save.

Add `user_scoped=true` query param to distinguish user-initiated flows from org-level setup:

```
/auth/mcp-oauth/start?mcp_server_id=N&org_slug=S&user_scoped=true
```

**`mcp_oauth_callback`**: If `org_user_id` is present in the decoded state, call
`save_mcp_server_oauth_for_user()` instead of `save_mcp_server_oauth()`.

Reference: `_InMemoryOAuthProvider` in `packages/csbot/src/csbot/compass_dev/mcp.py` shows the
existing OAuth wiring pattern.

---

## Phase 3: Per-Request Token Loading

### `packages/csbot/src/csbot/agents/anthropic/anthropic_agent.py`

Currently MCP servers are loaded at bot startup from `bot_config`. Loading them at startup means
all users share the same (org-scoped) token for the lifetime of the bot process.

Move MCP server loading into `stream_claude_response` (or its caller), passing `org_user_id` when
the user is available:

```python
mcp_servers = await storage.load_mcp_servers(
    organization_id=org_id,
    org_user_id=user.id if user else None,
)
```

This ensures each request gets the right token — user-scoped if connected, org-scoped as fallback.

---

## Phase 4: Auth-Required Prompting

When a server has no user-scoped token (`has_user_token=False`), the agent should surface a
message like:

> You need to connect your GitHub account to use erk. [Connect](<oauth-start-url>)

rather than silently using the bot identity. The `mcp_oauth_start` URL for the user:

```
/auth/mcp-oauth/start?mcp_server_id=N&org_slug=S&user_scoped=true
```

Detect the unconnected state from the `has_user_token` field in the loaded server config and
inject the prompt into the agent's system message or as a tool result.

---

## Critical File Paths

| File | Change |
|---|---|
| `packages/csbot/src/csbot/slackbot/storage/interface.py` | Add `save_mcp_server_oauth_for_user()` |
| `packages/csbot/src/csbot/slackbot/storage/postgresql.py` | Implement + update `_load_mcp_servers()` with user-scoped LEFT JOIN |
| `packages/csbot/src/csbot/slackbot/webapp/mcp_oauth.py` | Capture `org_user_id` in OAuth state; call user-scoped save in callback |
| `packages/csbot/src/csbot/agents/anthropic/anthropic_agent.py` | Load MCP servers per-request with `org_user_id` |

### Key References

- `packages/csbot/src/csbot/compass_dev/mcp.py` — `_InMemoryOAuthProvider` + `test-server-oauth` wiring
- `packages/csbot/src/csbot/slackbot/storage/schema_changes.py` — `mcp_server_auth` schema with `scope='user'` and `idx_mcp_server_auth_user` index

---

## Verification

1. `save_mcp_server_oauth_for_user` inserts `scope='user'` row; upsert on reconnect replaces it
2. `_load_mcp_servers(org_user_id=X)` returns user token when one exists, org token when not
3. `_load_mcp_servers(org_user_id=None)` returns org token (bot fallback unchanged)
4. OAuth callback with `user_scoped=true` and authenticated session saves user-scoped token
5. `stream_claude_response` receives user-scoped token as Bearer on MCP requests
6. End-to-end staging: `one_shot` PR actor is the human GitHub user; unconnected user sees auth prompt; bot fallback works

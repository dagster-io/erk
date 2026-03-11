# Plan: Per-User GitHub Attribution for erk-mcp

## Context

erk-mcp is deployed in Kubernetes with a shared GitHub App installation token (`GH_TOKEN` env var). All
`one_shot` PRs are attributed to the app identity (`elementl-devtools`) rather than the human Slack user.
This plan wires in per-user GitHub OAuth tokens so PRs show the real author.

The core mechanism: `GH_TOKEN` in the subprocess env determines which GitHub identity `erk json one-shot`
uses. Injecting a per-user `GH_TOKEN` override into that env is sufficient — no `ErkContext` changes needed.

## Architecture Overview

```
One-time user authorization:
  Compass detects no user-scoped erk-mcp token for this user
    → triggers MCP OAuth flow for erk-mcp
    → user authorizes on GitHub via erk-mcp's OAuthProxy
    → erk-mcp issues its own JWT, stores GitHub token internally
    → Compass stores erk-mcp JWT with scope='user' for this org_user_id

Per-request flow:
  Compass loads user-scoped erk-mcp JWT → sends Authorization: Bearer <user-jwt>
    → FastMCP validates JWT (RequireAuthMiddleware)
    → GitHubTokenMiddleware looks up GitHub token by JWT sub claim
    → sets ContextVar[github_token]
    → MachineCommandTool.run() reads ContextVar
    → subprocess.run(["erk", ...], env={**os.environ, "GH_TOKEN": user_token})
    → submitted_by = remote.get_authenticated_user() → real GitHub user
```

Fallback: if no user-scoped token, Compass uses the org-scoped token (bot identity).

---

## erk-mcp Changes

### Phase 1: Subprocess env override

**Modify `packages/erk-mcp/src/erk_mcp/server.py`**

Add `env_override` param to `_run_erk_json()`, read ContextVar in `MachineCommandTool.run()`:

```python
def _run_erk_json(
    command_path: tuple[str, ...],
    params: dict[str, Any],
    *,
    env_override: dict[str, str] | None = None,
) -> str:
    result = subprocess.run(
        ["erk", *command_path],
        input=json.dumps(params),
        capture_output=True,
        text=True,
        check=False,
        env=env_override,  # None = inherit process env (existing behavior)
    )
    return result.stdout
```

```python
# In MachineCommandTool.run():
user_token = get_request_github_token()  # reads ContextVar
env_override = {**os.environ, "GH_TOKEN": user_token} if user_token is not None else None
result = await to_thread.run_sync(
    lambda: _run_erk_json(path, params, env_override=env_override)
)
```

**New `packages/erk-mcp/src/erk_mcp/request_context.py`**

ContextVar for per-request GitHub token. Python asyncio propagates ContextVar snapshots to threads
spawned via `anyio.to_thread.run_sync` — value set in async middleware is readable in the sync function.

```python
from contextvars import ContextVar, Token

_github_token_for_request: ContextVar[str | None] = ContextVar(
    "_github_token_for_request", default=None
)

def set_request_github_token(token: str) -> Token[str | None]: ...
def get_request_github_token() -> str | None: ...
def reset_request_github_token(token: Token[str | None]) -> None: ...
```

### Phase 2: GitHub OAuth AS Provider

**New `packages/erk-mcp/src/erk_mcp/github_auth_provider.py`**

Implements the MCP SDK's `OAuthAuthorizationServerProvider` interface — the same interface used by
`_InMemoryOAuthProvider` in `dagster-compass/packages/csbot/src/csbot/compass_dev/mcp.py` (which is the
reference implementation). Compass's existing MCP OAuth discovery works unchanged because erk-mcp
publishes its own `/.well-known/oauth-authorization-server` at the same origin.

Key method overrides vs the in-memory reference:

- **`authorize(client, params)`** — instead of auto-approving, redirect to `https://github.com/login/oauth/authorize` with GitHub client_id and the MCP `state` parameter preserved through the round-trip
- **`exchange_authorization_code(client, auth_code)`** — exchange with GitHub's token endpoint, store the GitHub access token in the GrantStore keyed by a generated `sub`, issue an erk-mcp `OAuthToken` wrapping that `sub`
- **`load_access_token(token)`** — validate the token string, look up the `sub` → confirm GitHub token still exists in GrantStore
- **`exchange_refresh_token(client, refresh_token, scopes)`** — refresh the underlying GitHub token via GitHub's refresh endpoint, update GrantStore, issue new erk-mcp tokens

Wired into erk-mcp via `auth_server_provider=` and `AuthSettings` (same API the test server uses):

```python
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from pydantic import AnyHttpUrl

def build_auth_settings(base_url: str) -> AuthSettings:
    return AuthSettings(
        issuer_url=AnyHttpUrl(base_url),
        resource_server_url=AnyHttpUrl(f"{base_url}/mcp"),
        client_registration_options=ClientRegistrationOptions(enabled=True),
    )
```

**Internal token store (`grant_store.py`)**:

```python
@dataclass(frozen=True)
class UserGrant:
    jwt_sub: str        # erk-mcp JWT sub claim
    github_token: str   # GitHub access token
    github_login: str   # GitHub username
    expires_at: str     # ISO 8601 UTC
    refresh_token: str
    refresh_token_expires_at: str

class GrantStore(ABC):
    @abstractmethod
    def get_grant(self, jwt_sub: str) -> UserGrant | None: ...
    @abstractmethod
    def put_grant(self, grant: UserGrant) -> None: ...
    @abstractmethod
    def delete_grant(self, jwt_sub: str) -> None: ...
```

`JsonFileGrantStore`: atomic JSON file writes, path from `ERK_MCP_GRANT_STORE_PATH`.
`FakeGrantStore`: test double with `put_calls`/`delete_calls` tracking.

**Token refresh (`token_refresh.py`)**: refreshes GitHub token when within 5 min of expiry, persists
updated grant, returns `None` if refresh token is expired.

### Phase 3: FastMCP Middleware

**New `packages/erk-mcp/src/erk_mcp/github_token_middleware.py`**

Reads the validated erk-mcp JWT (already verified by FastMCP's `RequireAuthMiddleware`), looks up the
associated GitHub token, and sets the ContextVar.

```python
from mcp.server.auth.middleware.auth_context import get_access_token
from fastmcp.server.middleware.middleware import Middleware

class GitHubTokenMiddleware(Middleware):
    def __init__(self, *, grant_store: GrantStore) -> None:
        self._grant_store = grant_store

    async def on_call_tool(self, context, call_next) -> ToolResult:
        access_token = _get_validated_token()  # from FastMCP auth context
        if access_token is None:
            return await call_next(context)  # unauthenticated → fallback to bot token

        grant = self._grant_store.get_grant(access_token.sub)
        if grant is None:
            return await call_next(context)  # no GitHub grant → fallback

        grant = refresh_grant_if_needed(grant, self._grant_store)
        if grant is None:
            return await call_next(context)  # refresh expired → fallback

        tok = set_request_github_token(grant.github_token)
        try:
            return await call_next(context)
        finally:
            reset_request_github_token(tok)
```

**Note**: No `X-Slack-User-Id` header needed. The Bearer token carries user identity.

### Phase 4: Server wiring

**Modify `packages/erk-mcp/src/erk_mcp/__main__.py`**:

```python
def main() -> None:
    args = _parse_args(None)
    if args.transport == "stdio":
        create_mcp().run()
    else:
        grant_store = build_grant_store()
        oauth_proxy = build_github_oauth_proxy(
            base_url=os.environ["ERK_MCP_BASE_URL"],
            grant_store=grant_store,
            github_client_id=os.environ["ERK_MCP_GITHUB_CLIENT_ID"],
            github_client_secret=os.environ["ERK_MCP_GITHUB_CLIENT_SECRET"],
        )
        mcp = create_mcp()
        mcp.add_middleware(GitHubTokenMiddleware(grant_store=grant_store))
        mcp.run(transport=args.transport, host=args.host, port=args.port, auth=oauth_proxy)
```

### New K8s secrets

| Variable | Purpose |
|---|---|
| `ERK_MCP_GRANT_STORE_PATH` | Path for JSON grant store (K8s mounted volume) |
| `ERK_MCP_GITHUB_CLIENT_ID` | GitHub OAuth App client_id |
| `ERK_MCP_GITHUB_CLIENT_SECRET` | GitHub OAuth App client_secret |
| `ERK_MCP_BASE_URL` | Public URL of erk-mcp (e.g. `https://erk-mcp.example.com`) |

---

## dagster-compass Changes

The schema already has `scope='user'` and `org_user_id` in `mcp_server_auth`. The application layer
just needs to activate it.

### Storage changes

**`packages/csbot/src/csbot/slackbot/storage/interface.py`**

Add user-scoped save method:
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

**`packages/csbot/src/csbot/slackbot/storage/postgresql.py`**

Implement with `scope='user', org_user_id=<id>` (upsert via `idx_mcp_server_auth_user` index).

Update `_load_mcp_servers()` to accept optional `org_user_id` and LEFT JOIN user-scoped auth,
preferring it over org-scoped when available:
```sql
LEFT JOIN mcp_server_auth ma_org ON ms.id = ma_org.mcp_server_id AND ma_org.scope = 'organization'
LEFT JOIN mcp_server_auth ma_user ON ms.id = ma_user.mcp_server_id
    AND ma_user.scope = 'user' AND ma_user.org_user_id = %(org_user_id)s
-- COALESCE: prefer user-scoped token
COALESCE(ma_user.encrypted_access_token, ma_org.encrypted_access_token) AS encrypted_access_token,
...
```

### OAuth flow: capture user identity

**`packages/csbot/src/csbot/slackbot/webapp/mcp_oauth.py`**

Update `mcp_oauth_start` to require user session (already available via `ViewerContext`/cookies) and
pass `org_user_id` through the OAuth state parameter.

Update `mcp_oauth_callback`: if `org_user_id` is present in state, call
`save_mcp_server_oauth_for_user()` instead of `save_mcp_server_oauth()`.

### MCP token loading: per-request

**`packages/csbot/src/csbot/agents/anthropic/anthropic_agent.py`** (or the caller)

Currently MCP servers are loaded at bot startup from `bot_config`. To support per-user tokens,
load fresh server configs at request time in `stream_claude_response`, passing `org_user_id`:

```python
# In stream_claude_response, when user is available:
mcp_servers = await storage.load_mcp_servers(
    organization_id=org_id,
    org_user_id=user.id if user else None,
)
```

### Auth-required prompting

Currently the agent silently skips MCP servers with expired tokens. Change to prompt the user:
when a server has no auth or expired auth for this user, the agent should surface a message like
_"You need to connect your GitHub account to use erk. [Connect](<oauth-start-url>)"_ rather than
skipping silently.

The `mcp_oauth_start` URL for a user would be:
```
/auth/mcp-oauth/start?mcp_server_id=N&org_slug=S&user_scoped=true
```

### OAuth server URL split (Neil's observation)

Currently Compass truncates the MCP URL to its origin to find the OAuth AS. Since erk-mcp hosts
its own OAuthProxy at the same origin, **no change is needed for erk-mcp**. The existing discovery
(`GET /.well-known/oauth-protected-resource` → `GET /.well-known/oauth-authorization-server`) will
work transparently.

If a future MCP server needs a separate OAuth server URL, add an optional `oauth_server_url` field
to `McpServerConfig` — but that's not needed now.

---

## Critical File Paths

### erk repo

| File | Status |
|---|---|
| `packages/erk-mcp/src/erk_mcp/server.py` | Modify — `env_override` + ContextVar read |
| `packages/erk-mcp/src/erk_mcp/__main__.py` | Modify — wire OAuthProxy + middleware |
| `packages/erk-mcp/src/erk_mcp/request_context.py` | New |
| `packages/erk-mcp/src/erk_mcp/grant_store.py` | New — `GrantStore` ABC + `JsonFileGrantStore` + `FakeGrantStore` |
| `packages/erk-mcp/src/erk_mcp/token_refresh.py` | New |
| `packages/erk-mcp/src/erk_mcp/github_token_middleware.py` | New — `GitHubTokenMiddleware` |
| `packages/erk-mcp/src/erk_mcp/github_auth_provider.py` | New — `GitHubOAuthProvider(OAuthAuthorizationServerProvider)` |
| `packages/erk-mcp/tests/test_server.py` | Modify |
| `packages/erk-mcp/tests/test_grant_store.py` | New |
| `packages/erk-mcp/tests/test_github_token_middleware.py` | New |
| `packages/erk-mcp/tests/test_github_auth_provider.py` | New |

**Key reference**: `dagster-compass/packages/csbot/src/csbot/compass_dev/mcp.py` — `_InMemoryOAuthProvider` is the complete reference for the `OAuthAuthorizationServerProvider` interface that `GitHubOAuthProvider` will implement.

### dagster-compass repo

| File | Status |
|---|---|
| `packages/csbot/src/csbot/slackbot/storage/interface.py` | Modify — add `save_mcp_server_oauth_for_user()` |
| `packages/csbot/src/csbot/slackbot/storage/postgresql.py` | Modify — impl + update `_load_mcp_servers()` |
| `packages/csbot/src/csbot/slackbot/webapp/mcp_oauth.py` | Modify — capture `org_user_id` in state |
| `packages/csbot/src/csbot/agents/anthropic/anthropic_agent.py` | Modify — load user-scoped MCP tokens at request time |

### FastMCP APIs confirmed

- `FastMCP.add_middleware(Middleware)` — `server/server.py:402`
- `Middleware.on_call_tool()` — `server/middleware/middleware.py:156`
- `OAuthProxy(upstream_authorization_endpoint, upstream_token_endpoint, ...)` — `server/auth/oauth_proxy/proxy.py:228`
- `get_access_token` from `mcp.server.auth.middleware.auth_context` — for reading validated JWT in middleware

---

## What's Missing from Compass Docs

The `scope='user'` pattern in `mcp_server_auth` is undocumented. The schema implies a planned
per-user auth flow but there's no doc or comment explaining:
- When to use user-scoped vs org-scoped tokens
- How `_load_mcp_servers` is intended to be extended for user context
- The pattern for surfacing auth-required to individual Slack users

These should be documented in dagster-compass as the implementation lands.

---

## Verification

1. **ContextVar thread propagation** — unit test sets ContextVar in async, reads in thread via `anyio.to_thread.run_sync`
2. **Subprocess env injection** — patch `subprocess.run`, assert `env=` contains `GH_TOKEN=user_token`
3. **Middleware with valid grant** — `FakeGrantStore` seeded, assert ContextVar set and reset in `finally`
4. **Middleware with no grant** — no grant found → `call_next` invoked without ContextVar set (fallback)
5. **Well-known discovery** — `GET /.well-known/oauth-authorization-server` returns GitHub endpoints
6. **JsonFileGrantStore** — put/get/delete round-trip; atomic write `.tmp → rename`
7. **Token refresh** — expired token triggers GitHub refresh, updated grant persisted
8. **Compass user-scoped storage** — `save_mcp_server_oauth_for_user` inserts `scope='user'`; `_load_mcp_servers(org_user_id=X)` returns user token over org token
9. **End-to-end staging** — Slack `one_shot`: PR actor is the human GitHub user; unconnected user sees auth prompt; bot fallback works for org-level token
10. **Token security** — no token values in `_run_erk_json` stdout or ToolResult payloads
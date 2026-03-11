# Plan: Per-User GitHub Attribution for erk-mcp

## Context

erk-mcp is deployed in Kubernetes with a shared GitHub App installation token (`GH_TOKEN` env var). All
`one_shot` PRs are attributed to the app identity (`elementl-devtools`) rather than the human Slack user
who triggered the request. This plan wires in GitHub App user access tokens so PRs show the actual user.

The core mechanism is simple: `GH_TOKEN` in the subprocess environment determines which GitHub identity
`erk json one-shot` uses. Injecting a per-user `GH_TOKEN` override into that subprocess env is sufficient —
no `ErkContext` changes needed. The full plan adds the OAuth layer, token storage, and Slack contract on top.

## Architecture Overview

```
Slack bot → HTTP POST to /mcp (with X-Slack-User-Id header)
  → SlackUserMiddleware (FastMCP Middleware.on_call_tool)
      reads header, looks up UserGrant in GrantStore
      sets ContextVar[user_token]
  → MachineCommandTool.run()
      reads ContextVar, builds env_override
  → subprocess.run(["erk", ...], env={**os.environ, "GH_TOKEN": user_token})
      → gh auth token → returns user_token
      → submitted_by = remote.get_authenticated_user() → GitHub user
```

Fallback: if no `X-Slack-User-Id` header or no stored grant, the subprocess inherits the process-level
`GH_TOKEN` (bot token) unchanged.

---

## Phase 1: Request-Scoped Token Injection (erk-mcp plumbing)

### New: `packages/erk-mcp/src/erk_mcp/request_context.py`

ContextVar holding the per-request GitHub token. Python asyncio propagates ContextVar snapshots to threads
spawned via `anyio.to_thread.run_sync`, so the value set in async middleware is readable in the sync
subprocess-dispatch function.

```python
from contextvars import ContextVar, Token

_github_token_for_request: ContextVar[str | None] = ContextVar(
    "_github_token_for_request", default=None
)

def set_request_github_token(token: str) -> Token[str | None]:
    return _github_token_for_request.set(token)

def get_request_github_token() -> str | None:
    return _github_token_for_request.get()

def reset_request_github_token(token: Token[str | None]) -> None:
    _github_token_for_request.reset(token)
```

### Modify: `packages/erk-mcp/src/erk_mcp/server.py`

Add `env_override` parameter to `_run_erk_json()`:

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
        env=env_override,   # None = inherit process env (existing behavior)
    )
    return result.stdout
```

In `MachineCommandTool.run()`, read the ContextVar and build the env override:

```python
import os
from erk_mcp.request_context import get_request_github_token

async def run(self, arguments: dict[str, Any]) -> ToolResult:
    # ... existing None filter ...
    path = self.cli_command_path
    user_token = get_request_github_token()
    env_override = {**os.environ, "GH_TOKEN": user_token} if user_token is not None else None
    result = await to_thread.run_sync(
        lambda: _run_erk_json(path, params, env_override=env_override)
    )
    return self.convert_result(result)
```

---

## Phase 2: Token Storage

### New: `packages/erk-mcp/src/erk_mcp/grant_store.py`

**`UserGrant`** — frozen dataclass:

```python
@dataclass(frozen=True)
class UserGrant:
    slack_user_id: str
    github_login: str
    access_token: str
    refresh_token: str
    access_token_expires_at: str   # ISO 8601 UTC
    refresh_token_expires_at: str  # ISO 8601 UTC
```

**`GrantStore`** ABC:

```python
class GrantStore(ABC):
    @abstractmethod
    def get_grant(self, slack_user_id: str) -> UserGrant | None: ...
    @abstractmethod
    def put_grant(self, grant: UserGrant) -> None: ...
    @abstractmethod
    def delete_grant(self, slack_user_id: str) -> None: ...
```

**`JsonFileGrantStore`** — production implementation:
- Backed by `ERK_MCP_GRANT_STORE_PATH` env var (raise `RuntimeError` at startup if absent)
- Default path: `/var/run/erk-mcp/grants.json`
- Stores `{slack_user_id: {grant fields}}` JSON
- Atomic writes: write to `.tmp` then `os.replace()` to prevent partial reads
- No in-memory cache (re-read on every `get_grant`) — safe for single-replica K8s

**`FakeGrantStore`** — test double, tracks `put_calls` and `delete_calls` lists.

**`build_grant_store()`** — factory function that reads env vars and returns a `JsonFileGrantStore`.

### New: `packages/erk-mcp/src/erk_mcp/token_refresh.py`

```python
def refresh_grant_if_needed(grant: UserGrant, store: GrantStore) -> UserGrant | None:
    """Refresh access token if expiry is within 5 minutes. Returns updated grant or None."""
```

Compares `grant.access_token_expires_at` to `datetime.now(UTC) + timedelta(minutes=5)`.
On success: builds new `UserGrant`, calls `store.put_grant()`, returns updated grant.
On refresh token expiry: returns `None`.

---

## Phase 3: FastMCP Middleware

### New: `packages/erk-mcp/src/erk_mcp/slack_user_middleware.py`

```python
from fastmcp.server.http import _current_http_request
from fastmcp.server.middleware.middleware import Middleware, MiddlewareContext, CallNext
from erk_mcp.grant_store import GrantStore
from erk_mcp.request_context import set_request_github_token, reset_request_github_token
from erk_mcp.token_refresh import refresh_grant_if_needed

SLACK_USER_HEADER = "x-slack-user-id"

class SlackUserMiddleware(Middleware):
    def __init__(self, *, grant_store: GrantStore) -> None:
        self._grant_store = grant_store

    async def on_call_tool(self, context, call_next) -> ToolResult:
        slack_user_id = self._get_slack_user_id()

        if slack_user_id is None:
            return await call_next(context)  # no header → fallback to process GH_TOKEN

        grant = self._grant_store.get_grant(slack_user_id)

        if grant is None:
            return self._auth_required_result(slack_user_id)

        grant = refresh_grant_if_needed(grant, self._grant_store)
        if grant is None:
            return self._auth_required_result(slack_user_id)

        tok = set_request_github_token(grant.access_token)
        try:
            return await call_next(context)
        finally:
            reset_request_github_token(tok)

    def _get_slack_user_id(self) -> str | None:
        request = _current_http_request.get()
        if request is None:
            return None  # stdio transport
        return request.headers.get(SLACK_USER_HEADER)

    def _auth_required_result(self, slack_user_id: str) -> ToolResult:
        # Returns ToolResult with TextContent JSON:
        # {"success": false, "error_type": "github_auth_required",
        #  "slack_user_id": "...", "message": "..."}
        ...
```

---

## Phase 4: GitHub App OAuth (device flow) + Slack Contract

### New: `packages/erk-mcp/src/erk_mcp/github_oauth.py`

Uses `httpx` (already a transitive dep via fastmcp) for direct GitHub API calls — no `gh` CLI.

Key dataclasses:
- `DeviceFlowStart` — `device_code`, `user_code`, `verification_uri`, `expires_in`, `interval`
- `DeviceFlowToken` — `access_token`, `refresh_token`, `expires_in`, `refresh_token_expires_in`
- `DeviceFlowPending`, `DeviceFlowExpired`

Key functions:
- `start_device_flow(*, client_id: str) -> DeviceFlowStart`
- `poll_device_flow(*, client_id: str, device_code: str) -> DeviceFlowToken | DeviceFlowPending | DeviceFlowExpired`
- `refresh_access_token(*, client_id, client_secret, refresh_token) -> DeviceFlowToken | None`
- `get_github_login(*, access_token: str) -> str`

**In-memory pending flow tracking** (module-level, single-process OK):
```python
@dataclass(frozen=True)
class PendingFlow:
    slack_user_id: str
    device_code: str
    expires_at: float  # monotonic time

_pending_flows: dict[str, PendingFlow] = {}  # poll_token -> PendingFlow
```

### Custom routes on FastMCP server

Added in `__main__.py` via `@mcp.custom_route(...)` decorator:

**`POST /auth/github/start`**
- Body: `{"slack_user_id": "U123"}`
- Calls `start_device_flow()`, stores `PendingFlow` keyed by UUID `poll_token`
- Returns: `{"user_code": "ABCD-1234", "verification_uri": "...", "expires_in": 900, "poll_token": "<uuid>"}`
- The `device_code` is never returned to the caller

**`POST /auth/github/poll`**
- Body: `{"poll_token": "<uuid>"}`
- Calls `poll_device_flow()` with the stored `device_code`
- On `DeviceFlowToken`: calls `get_github_login()`, builds `UserGrant`, calls `store.put_grant()`, cleans up pending
- Returns: `{"status": "pending"}` or `{"status": "authorized", "github_login": "username"}`

**`POST /auth/github/revoke`**
- Body: `{"slack_user_id": "U123"}`
- Calls `store.delete_grant(slack_user_id)`
- Returns: `{"status": "revoked"}`

All auth routes validate a shared secret header `X-Internal-Auth` against `ERK_MCP_INTERNAL_SECRET` env var
to restrict access to the trusted Slack bot. Requests missing or with wrong secret → 403.

### Slack bot responsibilities

1. Add `X-Slack-User-Id: <slack_user_id>` to every MCP tool call request
2. On `error_type == "github_auth_required"`:
   - POST `/auth/github/start`
   - DM the user: "Authorize GitHub at **github.com/login/device** using code **ABCD-1234**"
   - Poll `/auth/github/poll` until `authorized` or expired
   - On `authorized`: reply to user confirming connection, optionally retry the original action
   - On expired: DM user that the code expired and they can try again

### New environment variables (K8s secrets)

| Variable | Purpose |
|---|---|
| `ERK_MCP_GRANT_STORE_PATH` | Path to grant store JSON file (mounted volume) |
| `ERK_MCP_GITHUB_CLIENT_ID` | GitHub App client_id |
| `ERK_MCP_GITHUB_CLIENT_SECRET` | GitHub App client_secret (for token refresh) |
| `ERK_MCP_INTERNAL_SECRET` | Shared secret for `/auth/github/*` routes |

---

## Modify: `packages/erk-mcp/src/erk_mcp/__main__.py`

```python
def main() -> None:
    args = _parse_args(None)
    mcp = create_mcp()

    if args.transport == "stdio":
        mcp.run()
    else:
        grant_store = build_grant_store()
        mcp.add_middleware(SlackUserMiddleware(grant_store=grant_store))
        _register_auth_routes(mcp, grant_store)
        mcp.run(transport=args.transport, host=args.host, port=args.port)
```

`_register_auth_routes(mcp, grant_store)` applies the `@mcp.custom_route()` decorators for the three auth endpoints. It lives in a new `auth_routes.py` module.

---

## Critical File Paths

| File | Status | Change |
|---|---|---|
| `packages/erk-mcp/src/erk_mcp/server.py` | Modify | `env_override` param + ContextVar read in `MachineCommandTool.run()` |
| `packages/erk-mcp/src/erk_mcp/__main__.py` | Modify | Wire middleware + auth routes for HTTP transport |
| `packages/erk-mcp/src/erk_mcp/request_context.py` | New | ContextVar module |
| `packages/erk-mcp/src/erk_mcp/grant_store.py` | New | `UserGrant`, `GrantStore` ABC, `JsonFileGrantStore`, `FakeGrantStore` |
| `packages/erk-mcp/src/erk_mcp/token_refresh.py` | New | `refresh_grant_if_needed()` |
| `packages/erk-mcp/src/erk_mcp/slack_user_middleware.py` | New | `SlackUserMiddleware` |
| `packages/erk-mcp/src/erk_mcp/github_oauth.py` | New | Device flow + refresh + pending flow tracking |
| `packages/erk-mcp/src/erk_mcp/auth_routes.py` | New | `_register_auth_routes()` with three endpoints |
| `packages/erk-mcp/tests/test_server.py` | Modify | Add token injection tests |
| `packages/erk-mcp/tests/test_grant_store.py` | New | `JsonFileGrantStore` round-trip + atomic write |
| `packages/erk-mcp/tests/test_slack_user_middleware.py` | New | Middleware unit tests with `FakeGrantStore` |
| `packages/erk-mcp/tests/test_github_oauth.py` | New | Device flow tests with mocked httpx |
| `packages/erk-mcp/tests/test_auth_routes.py` | New | Auth endpoint tests |

### FastMCP APIs confirmed available

- `FastMCP.add_middleware(middleware: Middleware)` — `server/server.py:402`
- `Middleware.on_call_tool()` hook — `server/middleware/middleware.py:156`
- `_current_http_request: ContextVar[Request | None]` — `server/http.py:64` (private, stable pattern)
- `@mcp.custom_route(path, methods)` decorator — `server/mixins/transport.py:97`

---

## Verification

1. **ContextVar thread propagation** — unit test: set ContextVar in async context, read in thread via `anyio.to_thread.run_sync`, assert value visible
2. **Subprocess env injection** — unit test: patch `subprocess.run`, call `_run_erk_json` with `env_override`, assert `subprocess.run` received `env=env_override` with `GH_TOKEN=<user_token>`
3. **Middleware with connected user** — unit test: `SlackUserMiddleware` + `FakeGrantStore` with seeded grant, assert ContextVar set to grant's access token and reset after call
4. **Middleware with unconnected user** — unit test: header present but no grant → assert `ToolResult` JSON has `error_type == "github_auth_required"`
5. **Middleware stdio fallback** — unit test: `_current_http_request` is `None` → calls `call_next` without setting ContextVar
6. **JsonFileGrantStore round-trip** — unit test: `put_grant` then `get_grant` returns same grant; atomic write (`.tmp` → rename)
7. **Token refresh** — unit test: expired access token triggers `refresh_access_token()`, updated grant persisted
8. **Device flow endpoints** — unit tests with mocked `httpx`: start returns `user_code` + `poll_token`; poll returns `pending` then `authorized`; grant stored on `authorized`
9. **End-to-end staging** — Slack-triggered `one_shot`: verify PR actor is the human GitHub user; verify bot fallback still works for users with no grant
10. **Token security** — grep `_run_erk_json` stdout and all ToolResult payloads; assert no token value surfaces

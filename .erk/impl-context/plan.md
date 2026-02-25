# Plan: Add Lightweight HTTP Webhook Server (Starlette)

**Part of Objective #8036, Node 2.1**

## Context

The erkbot currently communicates with Slack exclusively via Socket Mode (WebSocket). Node 2.1 adds a Starlette HTTP server that runs alongside Socket Mode to receive incoming webhook callbacks. Later nodes (2.2-2.5) will add the actual webhook handler for one-shot completion routing, token validation, and tests. This node focuses solely on the server infrastructure and a health check endpoint.

## Changes

### 1. Add dependencies to `pyproject.toml`

**File:** `packages/erkbot/pyproject.toml`

Add `starlette>=0.41.0` and `uvicorn[standard]>=0.32.0` to `dependencies`.

### 2. Add webhook config fields to `config.py`

**File:** `packages/erkbot/src/erkbot/config.py`

Add three fields to `Settings`:

```python
# Webhook server config
webhook_enabled: bool = Field(False, alias="ERK_WEBHOOK_ENABLED")
webhook_host: str = Field("0.0.0.0", alias="ERK_WEBHOOK_HOST")
webhook_port: int = Field(8080, alias="ERK_WEBHOOK_PORT")
```

Defaults to disabled so existing deployments are unaffected.

### 3. Create `webhook.py` module

**New file:** `packages/erkbot/src/erkbot/webhook.py`

Three functions:
- `healthz(request) -> JSONResponse` — returns `{"status": "ok"}`
- `create_webhook_app() -> Starlette` — factory with `/healthz` route
- `create_webhook_server(*, app, host, port) -> uvicorn.Server` — factory returning configured server (not started)

Routes defined as a list for easy extension by Node 2.2.

### 4. Modify `cli.py` to run both servers concurrently

**File:** `packages/erkbot/src/erkbot/cli.py`

Change from:
```python
await handler.start_async()
```

To:
```python
coros: list[Coroutine[Any, Any, None]] = [handler.start_async()]
if settings.webhook_enabled:
    webhook_app = create_webhook_app()
    server = create_webhook_server(app=webhook_app, host=..., port=...)
    coros.append(server.serve())
await asyncio.gather(*coros)
```

`asyncio.gather()` provides fail-fast: if either server crashes, the process exits.

### 5. Update existing test helper and add new tests

**File:** `packages/erkbot/tests/test_cli.py`

- Add `mock.webhook_enabled = False` to `_make_settings_mock()` — prevents existing tests from hitting the webhook code path (MagicMock attributes are truthy by default)
- Add test: webhook disabled (default) — `gather` called with 1 coroutine
- Add test: webhook enabled — `gather` called with 2 coroutines, `create_webhook_server` called with correct host/port

**File:** `packages/erkbot/tests/test_config.py`

- Add test: webhook defaults (`enabled=False`, `host=0.0.0.0`, `port=8080`)
- Add test: webhook from env vars

**New file:** `packages/erkbot/tests/test_webhook.py`

Uses Starlette's synchronous `TestClient` (no real server needed):
- `test_healthz_returns_ok` — GET /healthz returns 200, `{"status": "ok"}`
- `test_unknown_route_returns_404` — GET /nonexistent returns 404
- `test_healthz_post_returns_405` — POST /healthz returns 405
- `test_creates_server_with_config` — verify host/port on created server

## Files Summary

| File | Action |
|------|--------|
| `packages/erkbot/pyproject.toml` | Add starlette, uvicorn deps |
| `packages/erkbot/src/erkbot/config.py` | Add 3 webhook settings fields |
| `packages/erkbot/src/erkbot/webhook.py` | **New** — app factory, health route, server factory |
| `packages/erkbot/src/erkbot/cli.py` | Use `asyncio.gather()`, conditionally start webhook |
| `packages/erkbot/tests/test_config.py` | Add webhook config tests |
| `packages/erkbot/tests/test_webhook.py` | **New** — health check and server tests |
| `packages/erkbot/tests/test_cli.py` | Fix mock helper, add webhook enabled/disabled tests |

## Verification

1. `uv sync` in `packages/erkbot/` to install new deps
2. Run unit tests: `make test` in `packages/erkbot/`
3. Run linting/typing: `make lint` and `make typecheck` in `packages/erkbot/`
4. Manual smoke test: set `ERK_WEBHOOK_ENABLED=true` in `.env`, start bot, `curl localhost:8080/healthz`

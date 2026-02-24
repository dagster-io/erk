---
title: Bolt Async Dispatch Testing Pattern
read_when:
  - "working on erk-slack-bot integration tests"
  - "testing Slack handlers without live connection"
  - "working with slack_bolt AsyncApp dispatch"
category: testing
tripwires:
  - action: "calling handler functions directly with AsyncMock say/client"
    warning: "Dispatch through AsyncApp via AsyncBoltRequest for integration tests."
  - action: "using hardcoded port numbers for mock server"
    warning: "Use port=0 for auto-assigned port to avoid CI conflicts."
  - action: "mock chat.postMessage response missing ts field"
    warning: "Always include ts in response - extract_slack_message_ts depends on it."
  - action: "using asyncio.sleep() to wait for Bolt handler completion"
    warning: "Use dispatch_and_settle() from conftest — it awaits all background tasks deterministically."
---

# Bolt Async Dispatch Testing Pattern

Integration testing pattern for slack_bolt AsyncApp handlers using mock HTTP servers and real Bolt dispatch, adapted from the bolt-python SDK's own test suite.

## Architecture

```
Test
  -> build AsyncBoltRequest (signed headers + JSON body)
  -> app.async_dispatch(request)
  -> Bolt middleware pipeline
  -> handler (event/say/client injected by Bolt)
  -> AsyncWebClient calls mock HTTP server
  -> assertions on mock server received requests
```

## Core Pattern

### AsyncBoltRequest Construction

```python
import json
import time
from slack_bolt.request.async_request import AsyncBoltRequest
from slack_sdk.signature import SignatureVerifier

signing_secret = "test-signing-secret"
verifier = SignatureVerifier(signing_secret)

body = json.dumps({
    "type": "event_callback",
    "event": {
        "type": "app_mention",
        "user": "U123",
        "text": "<@B123> plan list",
        "channel": "C123",
        "ts": "1234567890.000001",
    },
    "event_id": "Ev123",
    "team_id": "T123",
})

timestamp = str(int(time.time()))
signature = verifier.generate_signature(timestamp=timestamp, body=body)

request = AsyncBoltRequest(
    body=body,
    headers={
        "content-type": ["application/json"],
        "x-slack-signature": [signature],
        "x-slack-request-timestamp": [timestamp],
    },
)
```

Key details:

- `body` must be a JSON string (not dict)
- Headers are `dict[str, list[str]]` (list values, not plain strings)
- Timestamp must be recent (within 5 minutes) or signature verification fails
- Signature computed via `SignatureVerifier.generate_signature()`

### Handler Dependency Injection

Bolt injects these by parameter name:

| Parameter | Type           | What Bolt Injects                              |
| --------- | -------------- | ---------------------------------------------- |
| `event`   | dict           | The event payload from `body["event"]`         |
| `say`     | AsyncSay       | Bound to event channel, calls chat.postMessage |
| `client`  | AsyncWebClient | Token-authenticated API client                 |
| `body`    | dict           | Full request body                              |
| `context` | BoltContext    | Request context with bot info                  |

### Mock Server Requirements

Endpoint-specific responses the mock server must handle:

| Endpoint            | Response                                                                                                           | Notes                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| `/auth.test`        | `{"ok": true, "url": "...", "team": "...", "user": "...", "team_id": "T123", "user_id": "U123", "bot_id": "B123"}` | Called during app init                             |
| `/chat.postMessage` | `{"ok": true, "ts": "<counter>", "channel": "C123"}`                                                               | `ts` required for `extract_slack_message_ts()`     |
| `/chat.update`      | `{"ok": true}`                                                                                                     | Configurable to return errors for fallback testing |
| `/reactions.add`    | `{"ok": true}`                                                                                                     | Configurable to return errors                      |
| Default             | `{"ok": true}`                                                                                                     | Catch-all for other endpoints                      |

### Request Tracking

Use queue-based `ReceivedRequests` for assertions. **Must call `drain()` first** to populate from the queue:

```python
received_requests.drain()  # Required before get_count/get_bodies
count = received_requests.get_count("/chat.postMessage")
bodies = received_requests.get_bodies("/chat.postMessage")
assert count == 2
assert "Running" in bodies[0]["text"]
```

> **Source**: See `packages/erkbot/tests/mock_web_api_server/received_requests.py` for the full `ReceivedRequests` API (`drain()`, `get_count()`, `get_bodies()`, `get_all_paths()`, `reset()`).

### Background Task Testing

Use `dispatch_and_settle` instead of `asyncio.sleep()` to await all background tasks spawned during dispatch. It tracks tasks via `asyncio.all_tasks()` diffing and handles both Bolt's `ensure_future()` handlers and app-level `create_task()` calls.

> **Source**: See `packages/erkbot/tests/integration/conftest.py` for the `dispatch_and_settle()` function signature and usage pattern.

## Event Body Formats

### app_mention

```json
{
  "type": "event_callback",
  "event": {
    "type": "app_mention",
    "user": "U123",
    "text": "<@B123> plan list",
    "channel": "C123",
    "ts": "1234567890.000001"
  },
  "event_id": "Ev123",
  "team_id": "T123"
}
```

### message (for ping)

```json
{
  "type": "event_callback",
  "event": {
    "type": "message",
    "user": "U123",
    "text": "ping",
    "channel": "C123",
    "ts": "1234567890.000001"
  },
  "event_id": "Ev123",
  "team_id": "T123"
}
```

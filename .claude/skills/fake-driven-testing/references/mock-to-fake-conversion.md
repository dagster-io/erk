---
name: fake-driven-testing-mock-to-fake-conversion
description: Converting tests that use unittest.mock into the gateway/fake pattern
---

# Mock-to-Fake Conversion

**Read this when**: You find tests using `unittest.mock.patch`, `@patch` decorators, or `MagicMock` that should use gateway fakes instead.

## Why This Happens

AI agents (and developers unfamiliar with the gateway pattern) often reach for `unittest.mock` when writing tests. This creates tests that are:

- **Coupled to import paths** — `@patch("myapp.services.subprocess.run")` breaks when code moves
- **Hard to read** — nested `mock.return_value.json.return_value` chains
- **Fragile** — tests break on refactoring even when behavior is unchanged

The fix is to convert these mocks into gateway fakes.

## Step 1: Audit What's Being Mocked

For each `patch(...)` call, identify the **system boundary** (tool or service), not the Python function:

| Mock target                                  | System boundary | What it simulates    |
| -------------------------------------------- | --------------- | -------------------- |
| `myapp.service.requests.get`                 | HTTP API        | API response         |
| `myapp.service.subprocess.run(["git", ...])` | Git             | Repository operation |
| `myapp.service.smtplib.SMTP.send_message`    | Email service   | Sending email        |

**Group mocks by test.** A single test patching 2-3 things together suggests those things form a unit covered by one gateway.

### The Critical Rule

> **`subprocess.run` is never the right gateway boundary.**

The gateway should be named after the _tool_ being called, not the mechanism:

| Mock target                                  | Wrong gateway      | Right gateway    |
| -------------------------------------------- | ------------------ | ---------------- |
| `subprocess.run(["git", ...])`               | `SubprocessRunner` | `GitGateway`     |
| `subprocess.run(["aws", ...])`               | `ShellExecutor`    | `S3Gateway`      |
| `requests.get("https://api.stripe.com/...")` | `HttpClient`       | `PaymentGateway` |
| `smtplib.SMTP.send_message(...)`             | `SmtpWrapper`      | `EmailGateway`   |

Name the gateway after what it represents, not how it executes.

## Step 2: Check for Existing Gateways

Before creating anything new, check if a gateway already exists:

```bash
# Search for existing ABCs
grep -r "class.*ABC" src/myapp/gateways/

# Search for existing fakes
grep -r "class Fake" tests/fakes/
```

**Priority when multiple gateways match:**

1. A gateway that covers ALL mocked targets in a test
2. A gateway at the highest behavioral level (e.g., `PaymentGateway.charge()` rather than `HttpClient.post()`)
3. The lowest-level matching gateway as a last resort

If an existing gateway covers the mocked behavior, skip to Step 4.

## Step 3: Create the Gateway (If Needed)

Follow the standard three-file pattern (see `gateway-architecture.md`):

```python
# src/myapp/gateways/user_api.py

from abc import ABC, abstractmethod

class UserApiClient(ABC):
    @abstractmethod
    def get_users(self) -> list[dict]:
        """Fetch users from API."""

class RealUserApiClient(UserApiClient):
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def get_users(self) -> list[dict]:
        import requests
        response = requests.get(
            f"{self._base_url}/users",
            headers={"Authorization": f"Bearer {self._api_key}"}
        )
        response.raise_for_status()
        return response.json()["users"]
```

```python
# tests/fakes/user_api.py

class FakeUserApiClient(UserApiClient):
    def __init__(self, *, users: list[dict] | None = None) -> None:
        self._users = users or []
        self._get_users_calls: list[None] = []

    def get_users(self) -> list[dict]:
        self._get_users_calls.append(None)
        return list(self._users)

    @property
    def get_users_call_count(self) -> int:
        return len(self._get_users_calls)
```

## Step 4: Make Source Code Injectable

Add the gateway as a constructor parameter:

```python
# Before:
class DataSyncService:
    def sync(self) -> None:
        import requests
        users = requests.get("https://api.example.com/users").json()["users"]
        ...

# After:
class DataSyncService:
    def __init__(self, *, user_api: UserApiClient) -> None:
        self._user_api = user_api

    def sync(self) -> None:
        users = self._user_api.get_users()
        ...
```

Update production wiring to pass the real implementation:

```python
service = DataSyncService(user_api=RealUserApiClient(base_url=..., api_key=...))
```

## Step 5: Rewrite the Tests

```python
# Before:
@patch("myapp.services.requests.get")
def test_sync_fetches_users(mock_get):
    mock_get.return_value.json.return_value = {"users": [{"id": 1, "name": "Alice"}]}

    service = DataSyncService()
    service.sync()

    mock_get.assert_called_once()

# After:
def test_sync_fetches_users() -> None:
    fake_api = FakeUserApiClient(users=[{"id": 1, "name": "Alice"}])
    service = DataSyncService(user_api=fake_api)

    service.sync()

    assert fake_api.get_users_call_count == 1
```

## Step 6: Verify

Run the affected tests, then lint and type-check:

```bash
pytest tests/unit/test_sync_service.py -v
mypy src/myapp/services/
```

## When Monkeypatch Is Still OK

Not everything needs a gateway. Monkeypatch (pytest's built-in) is acceptable for **process-level globals**:

```
Is there a gateway for this operation?
├── YES -> Use the fake gateway
│
└── NO -> Should there be a gateway?
    ├── YES -> Create the gateway, then use its fake
    │
    └── NO -> Is it a process-level global?
        ├── YES -> monkeypatch is acceptable
        │         (environment variables, Path.home(), locale)
        │
        └── NO -> Create a gateway
```

**Acceptable monkeypatch uses:**

- `monkeypatch.setenv("API_KEY", "test_value")` — environment variables
- `monkeypatch.setattr(Path, "home", lambda: tmp_path)` — home directory isolation
- `monkeypatch.delenv("DEBUG", raising=False)` — removing env vars

**Not acceptable (need a gateway instead):**

- `monkeypatch.setattr(subprocess, "run", ...)` — bypasses gateway infrastructure
- `monkeypatch.setattr(requests, "get", ...)` — should be behind a gateway
- `@patch("module.function")` — unittest.mock should be replaced entirely

## Common Pitfalls

### Pitfall 1: Wrong gateway level

If `shutil.which("tool")` and `subprocess.run(["tool", ...])` are both mocked in the same test, the gateway should cover _both_ — something like `ToolGateway` with an `is_available()` method and operation methods. Don't create separate gateways for availability checks vs execution.

### Pitfall 2: subprocess-level gateways

If you find yourself designing a gateway called `ShellRunner`, `SubprocessGateway`, or `CommandRunner`, stop. That's still mocking at the wrong level. The gateway must be specific to the _tool_ being called.

### Pitfall 3: Forgetting production wiring

After adding a constructor parameter, update wherever the class is instantiated in production. Type checkers will catch this — run them.

### Pitfall 4: Multiple patches = wrong abstraction

Multiple `patch()` calls in one test is a red flag. A single fake should replace all of them. If you need 3+ patches, the gateway is probably at the wrong level of abstraction.

### Pitfall 5: Keeping unittest.mock "just for this one thing"

Once you have gateways, there's almost never a reason to keep `unittest.mock`. The exception is `monkeypatch` for process-level globals (see decision tree above).

## Related Documentation

- `gateway-architecture.md` - How to design gateway interfaces
- `non-ideal-states.md` - Designing return types for operations that can fail
- `patterns.md` - Constructor injection and mutation tracking
- `anti-patterns.md#mocking-what-you-dont-own` - Why mocking third-party libraries is fragile

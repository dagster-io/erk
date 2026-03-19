---
name: fake-driven-testing-non-ideal-states
description: Non-ideal states vs exceptions and how they shape gateway design
---

# Non-Ideal States vs Exceptions

**Read this when**: Designing gateway method return types, deciding how to handle errors in gateway interfaces, or implementing error injection in fakes.

## The Core Distinction

Non-ideal states are **optional outcomes visible in the type signature**. When a gateway method returns `UserCreated | UserAlreadyExists`, both possible outcomes are self-documenting — any reader (human or AI agent) can see from the signature alone what can happen and write control flow accordingly.

This is the fundamental advantage over exceptions: **Python exceptions are not knowable from the type signature.** You cannot determine what a function might throw without reading its implementation (and every implementation it calls). This makes exceptions hostile to agent-driven development and harder for humans to reason about.

The distinction:

- **Non-ideal states** — optional outcomes encoded in the return type. The caller can see them, branch on them, and continue. Self-documenting.
- **Exceptions** — invisible in the type signature. Used only when all callers terminate identically and no branching logic is needed.

This distinction drives how you design gateway method signatures, which in turn drives how fakes simulate error conditions.

## When to Use Exceptions

Use exceptions when **all callers terminate identically** — the error is just a message, no branching logic, no meaningful field inspection.

```python
class RealFileSystem(FileSystemGateway):
    def read_file(self, path: Path) -> str:
        """Read file contents. Raises if file doesn't exist."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_text(encoding="utf-8")
```

The fake is simple — it raises the same exception when configured to:

```python
class FakeFileSystem(FileSystemGateway):
    def __init__(self, *, files: dict[str, str] | None = None) -> None:
        self._files = files or {}

    def read_file(self, path: Path) -> str:
        key = str(path)
        if key not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[key]
```

## When to Use Non-Ideal States (Discriminated Unions)

Use non-ideal states when **callers branch on the error and continue** — different handling for different outcomes, field inspection, or type-safe continuation.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class UserCreated:
    """Success: user was created."""
    user_id: int

@dataclass(frozen=True)
class UserAlreadyExists:
    """Non-ideal state: email is taken."""
    email: str
    message: str

class UserGateway(ABC):
    @abstractmethod
    def create_user(self, email: str, name: str) -> UserCreated | UserAlreadyExists:
        """Create a user. Returns non-ideal state if email is taken."""
```

The caller branches on the result:

```python
result = gateway.create_user(email, name)
if isinstance(result, UserAlreadyExists):
    # Branch: suggest login instead
    click.echo(f"Account already exists for {result.email}")
    return
# Type narrowing: result is UserCreated
click.echo(f"Created user {result.user_id}")
```

## Decision Framework

| Question                                           | If Yes          | If No           |
| -------------------------------------------------- | --------------- | --------------- |
| Do callers branch on the error type?               | Non-ideal state | Exception       |
| Do callers inspect error fields (email, id, etc.)? | Non-ideal state | Exception       |
| Do callers continue after handling the error?      | Non-ideal state | Exception       |
| Do all callers just surface the message and stop?  | Exception       | Non-ideal state |

## Type Narrowing: Always Use isinstance()

**Always use `isinstance()` for type narrowing.** Never use truthiness checks, `.success` attributes, or any other mechanism.

```python
# CORRECT: isinstance() enables type narrowing
result = gateway.charge(card, amount)
if isinstance(result, PaymentDeclined):
    # Type checker knows: result is PaymentDeclined
    log(f"Declined: {result.reason}")
    return handle_decline(result)
# Type checker knows: result is ChargeSuccess
send_receipt(result.transaction_id)
```

```python
# WRONG: truthiness doesn't narrow types
if not result:  # Empty success markers are falsy!
    ...

# WRONG: attribute checks bypass the type system
if result.is_error:  # Type checker can't narrow from this
    ...
```

## Error Boundaries: Where try/except Belongs

In the gateway pattern, **only the Real implementation catches exceptions**. Fakes never use try/except.

| Implementation | Error mechanism                                           | Uses try/except? |
| -------------- | --------------------------------------------------------- | ---------------- |
| **ABC**        | Defines union return type                                 | No               |
| **Real**       | Catches subprocess/system exceptions, returns error types | **Yes**          |
| **Fake**       | Returns error types based on constructor params           | No               |

### Real: The Exception Boundary

The Real implementation is the only place where external systems raise exceptions. It catches them and converts to discriminated union types:

```python
class RealPaymentGateway(PaymentGateway):
    def charge(self, card: str, amount: float) -> ChargeSuccess | PaymentDeclined:
        response = self._http_client.post("/charges", json={
            "card": card, "amount": amount
        })
        if response.status_code == 402:
            data = response.json()
            return PaymentDeclined(
                reason=data["decline_reason"],
                card_last_four=card[-4:]
            )
        response.raise_for_status()  # Unexpected errors -> exception
        return ChargeSuccess(transaction_id=response.json()["id"])
```

**What gets caught:** Expected failure modes from external systems (HTTP 402, command exit codes, file-not-found).

**What doesn't get caught:** Programming errors (AttributeError, TypeError) — these should crash, not be masked.

### Fake: Constructor-Configured (No try/except)

Fakes never catch exceptions because they never call external systems. Error behavior is configured at construction time:

```python
class FakePaymentGateway(PaymentGateway):
    def __init__(
        self,
        *,
        decline_cards: dict[str, str] | None = None,
    ) -> None:
        self._decline_cards = decline_cards or {}
        self._charges: list[tuple[str, float]] = []

    def charge(self, card: str, amount: float) -> ChargeSuccess | PaymentDeclined:
        if card in self._decline_cards:
            return PaymentDeclined(
                reason=self._decline_cards[card],
                card_last_four=card[-4:]
            )
        self._charges.append((card, amount))
        return ChargeSuccess(transaction_id=f"fake-txn-{len(self._charges)}")
```

**Why no try/except?** There are no subprocess calls, no network requests, no filesystem operations. Error scenarios are predetermined by test setup, not discovered at runtime.

## Three Test Categories Per Operation

Every fake method that returns a discriminated union needs three test categories:

| Category              | What it verifies                         | Why it matters                                        |
| --------------------- | ---------------------------------------- | ----------------------------------------------------- |
| **Default success**   | No-arg construction returns success      | Proves fakes are zero-config for happy paths          |
| **Error injection**   | Constructor-configured error is returned | Proves failure paths work without modifying internals |
| **Mutation tracking** | Operations record calls via properties   | Proves assertions can verify what operations occurred |

```python
class TestCharge:
    """Tests for FakePaymentGateway.charge()"""

    def test_default_success(self) -> None:
        """No-arg fake returns success."""
        fake = FakePaymentGateway()
        result = fake.charge("4111111111111111", 50.0)
        assert isinstance(result, ChargeSuccess)

    def test_error_injection(self) -> None:
        """Constructor-configured decline is returned."""
        fake = FakePaymentGateway(
            decline_cards={"4000000000000002": "insufficient funds"}
        )
        result = fake.charge("4000000000000002", 50.0)
        assert isinstance(result, PaymentDeclined)
        assert result.reason == "insufficient funds"

    def test_mutation_tracking(self) -> None:
        """Successful charges are tracked."""
        fake = FakePaymentGateway()
        fake.charge("4111111111111111", 50.0)
        assert len(fake.charges) == 1
        assert fake.charges[0] == ("4111111111111111", 50.0)
```

Organize tests **by operation** (one test class per method), not by category.

## The Tracking-on-Error Decision

The most subtle design choice: should mutation tracking occur when the operation returns an error?

Ask: **"If the real operation fails, did a side effect still occur?"**

| Scenario                         | Track on error? | Rationale                                                  |
| -------------------------------- | --------------- | ---------------------------------------------------------- |
| Payment charge declined          | No              | No money moved — tracking would misrepresent what happened |
| Data sync attempted              | Yes             | The sync was attempted and may have partially applied      |
| File upload failed               | No              | Nothing was uploaded                                       |
| Database transaction rolled back | Yes             | The transaction was attempted                              |

**Implementation pattern:**

```python
# No side effect on failure -> check error FIRST, skip tracking
def charge(self, card: str, amount: float) -> ChargeSuccess | PaymentDeclined:
    if card in self._decline_cards:
        return PaymentDeclined(...)  # Return before tracking
    self._charges.append((card, amount))  # Track only on success
    return ChargeSuccess(...)

# Side effect on failure -> track FIRST, then check error
def sync_data(self, source: str) -> SyncComplete | SyncPartialFailure:
    self._sync_attempts.append(source)  # Always track the attempt
    if source in self._partial_failure_sources:
        return SyncPartialFailure(...)
    return SyncComplete(...)
```

## Anti-Patterns

### Using try/except in fakes

```python
# WRONG — fakes have no exceptions to catch
class FakePaymentGateway(PaymentGateway):
    def charge(self, card, amount):
        try:
            if card in self._decline_cards:
                return PaymentDeclined(...)
            return ChargeSuccess(...)
        except Exception as e:
            return PaymentDeclined(reason=str(e))  # Dead code
```

### Catching exceptions to return None

```python
# WRONG — masks the actual error
class RealApiClient(ApiClient):
    def get_user(self, user_id: int) -> dict | None:
        try:
            return self._http.get(f"/users/{user_id}").json()
        except Exception:
            return None  # Was it 404? 500? Network timeout?
```

Use discriminated unions to preserve error context:

```python
# CORRECT — caller can branch on the specific error
def get_user(self, user_id: int) -> UserData | UserNotFound | ApiError:
    ...
```

### Testing only the happy path

Every discriminated union method needs both success AND error tests. A fake that only tests success could silently break error injection for all consumers.

## Pattern Structure

**Success types**: Frozen dataclasses with useful fields (IDs, created resources), or empty markers when the operation itself is the result.

**Non-ideal state types**: Frozen dataclasses with `message: str` and descriptive fields.

```python
@dataclass(frozen=True)
class PaymentProcessed:
    transaction_id: str
    amount: float

@dataclass(frozen=True)
class InsufficientFunds:
    available: float
    requested: float
    message: str

@dataclass(frozen=True)
class CardDeclined:
    reason: str
    message: str

class PaymentGateway(ABC):
    @abstractmethod
    def charge(
        self, card: str, amount: float
    ) -> PaymentProcessed | InsufficientFunds | CardDeclined:
        """Process payment. Multiple non-ideal states for different failures."""
```

## Related Documentation

- `gateway-architecture.md` - Gateway interface design
- `patterns.md` - Constructor injection and error injection patterns
- `testing-strategy.md` - Layer 1 "fake-check" tests for fakes
- `anti-patterns.md` - What to avoid

---
title: Gateway Error Boundaries
read_when:
  - "implementing gateway error handling"
  - "converting gateway operations to discriminated unions"
  - "deciding where try/except blocks belong in gateways"
tripwires:
  - score: 8
    action: "try/except in fake.py or dry_run.py"
    warning: "Gateway error handling (try/except) belongs ONLY in real.py. Fake and dry-run implementations return error discriminants based on constructor params, they don't catch exceptions."
    context: "The 5-file gateway pattern has clear error boundary responsibilities. Real implementations catch and convert subprocess/system errors. Fakes simulate errors via constructor params. Dry-run always returns success."
---

# Gateway Error Boundaries

## The Core Principle

In erk's 5-file gateway pattern, **only real.py catches exceptions**. The other four files (abc.py, fake.py, dry_run.py, printing.py) never use try/except — they express failure through different mechanisms.

This separation exists because error boundaries serve different purposes:

- **Real implementations** defend against actual system failures (subprocess crashes, missing files, network timeouts)
- **Fake implementations** simulate failure modes for testing via constructor configuration
- **Dry-run implementations** model the success path for validation workflows
- **Printing implementations** delegate transparently without intercepting errors

## Why This Matters

### The Temptation to Add try/except Everywhere

When implementing a gateway method that can fail, it's tempting to add try/except blocks to all five files. This feels symmetric — "if real.py catches exceptions, shouldn't fake.py and dry_run.py do the same?"

**No.** The symmetry is in the _return type_ (discriminated unions), not the error handling mechanism.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py, FakeCommandExecutor.__init__ -->

Fakes like `FakeCommandExecutor` (in `packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py`) configure error behavior through constructor params, not try/except. Tests pass in pre-configured discriminants via params like `merge_should_succeed: bool` or `gist_create_error: str | None`.

### Real.py: Subprocess and System Boundaries

Real implementations wrap subprocess calls and file system operations — both sources of runtime exceptions. try/except converts these into discriminated union error types.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.update_pr_base_branch -->

See `RealGitHub.update_pr_base_branch()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the pattern: subprocess commands wrapped in try/except to gracefully handle gh CLI availability issues.

**Why catch exceptions here?**

1. Subprocess failures are unpredictable (process crashes, command not found, permission denied)
2. Callers need structured error information (type, message, context) to make branching decisions
3. LBYL philosophy: check for failure modes and convert to explicit discriminants

**What gets caught?**

- Subprocess execution failures (`CalledProcessError`, `FileNotFoundError`)
- System-level errors (disk full, permission denied, network timeouts)
- External command availability (gh not installed, not authenticated)

**What doesn't get caught?**

- Programming errors (AttributeError, TypeError) — these should crash, not be masked as "operation failed"
- Validation errors that should be caught upstream by caller preconditions

### Fake.py: Constructor-Configured Simulation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py, FakeGitHub.__init__ -->

Fake implementations like `FakeGitHub` (in `packages/erk-shared/src/erk_shared/gateway/github/fake.py`) use constructor params to control error scenarios. Check the `__init__` signature: `merge_should_succeed: bool = True`, `gist_create_error: str | None = None`, `pr_diff_error: str | None = None`.

Tests instantiate fakes with pre-configured failure modes:

```python
# Test setup (from test code, not copied from source)
fake = FakeGitHub(
    merge_should_succeed=False,
    gist_create_error="Rate limited"
)

# Method implementation returns discriminant based on constructor param
result = fake.merge_pr(repo_root, pr_number, ...)
# Returns MergeError without try/except
```

**Why no try/except in fakes?**

1. No subprocess calls = no runtime exceptions to catch
2. Error scenarios are predetermined by test setup, not discovered at runtime
3. Simpler implementation: direct conditional returns based on params
4. Tests are fast and deterministic (no subprocess overhead)

## Implementation Responsibilities by File

| File          | Error Mechanism                                    | Uses try/except? |
| ------------- | -------------------------------------------------- | ---------------- |
| `abc.py`      | Defines discriminated union return types           | No               |
| `real.py`     | Catches subprocess/system exceptions               | **Yes**          |
| `fake.py`     | Returns discriminants based on constructor         | No               |
| `dry_run.py`  | Always returns success discriminant                | No               |
| `printing.py` | Delegates to wrapped implementation (pass-through) | No               |

### abc.py: Type Definitions

Defines the method signature with discriminated union return type. No implementation, just the contract.

### real.py: The Exception Boundary

The only file with try/except blocks. Catches exceptions from subprocess calls and system operations, converts to discriminated union error types.

**Pattern:**

1. Wrap subprocess/system call in try/except
2. Check return codes or response data for expected failure modes
3. Return appropriate discriminant (success or specific error type)
4. Catch unexpected exceptions and return generic error discriminant

### fake.py: Constructor-Driven

Methods check constructor params and return discriminants directly. No exception handling because there are no subprocess calls.

**Pattern:**

1. Check relevant constructor param (e.g., `if self._merge_should_succeed:`)
2. Return success or error discriminant based on param
3. Track operation in internal state for test assertions

### dry_run.py: Success Path Only

Always returns success discriminants. Used for validation workflows where you want to check the command sequence without executing operations.

**Pattern:**

1. Log what would have been done
2. Return success discriminant
3. No error handling (failure scenarios aren't modeled in dry-run)

### printing.py: Transparent Wrapper

Logs the operation, delegates to wrapped implementation, returns whatever the wrapped implementation returns. No error handling — errors flow through from the wrapped gateway.

**Pattern:**

1. Log operation parameters
2. Delegate to `self._impl.method(...)`
3. Return the result (success or error discriminant)

## Anti-Patterns

### ❌ WRONG: try/except in Fake

```python
# DON'T DO THIS
class FakeGitHub(GitHub):
    def merge_pr(...) -> MergeResult | MergeError:
        try:
            # Fakes don't make subprocess calls, so this is pointless
            if not self._merge_should_succeed:
                return MergeError(message="Merge failed")
            return MergeResult()
        except Exception as e:
            # What exception would be caught here? None.
            return MergeError(message=str(e))
```

**Why wrong:** Fakes have no code that raises exceptions. The try/except adds ceremony without value.

### ❌ WRONG: try/except in Dry Run

```python
# DON'T DO THIS
class DryRunGitHub(GitHub):
    def merge_pr(...) -> MergeResult | MergeError:
        try:
            self._logger.log(f"Would merge PR #{pr_number}")
            return MergeResult()
        except Exception as e:
            # Dry run always succeeds, so this never executes
            return MergeError(message=str(e))
```

**Why wrong:** Dry-run models the success path. If an exception occurs, it's a programming error that should crash, not be caught.

### ❌ WRONG: Catching Exceptions to Return None/False

```python
# DON'T DO THIS
class RealGitHub(GitHub):
    def get_pr_diff(self, pr_number: int) -> str | None:
        try:
            result = run_subprocess([...])
            return result.stdout
        except Exception:
            return None  # Masks the actual error
```

**Why wrong:** Callers can't distinguish "no diff found" from "gh CLI not installed" from "network timeout". Use discriminated unions to preserve error context.

## Related Patterns

- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-file checklist covering abc.py, real.py, fake.py, dry_run.py, printing.py
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Return type design for operations that can fail
- [Subprocess Wrappers](subprocess-wrappers.md) - Subprocess execution patterns used in real.py
- [Fake-Driven Testing](../testing/fake-driven-testing.md) - How fakes enable fast, deterministic tests

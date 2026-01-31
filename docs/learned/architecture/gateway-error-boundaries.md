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

## The 5-File Gateway Pattern

The gateway ABC implementation pattern (see [Gateway ABC Implementation](gateway-abc-implementation.md)) uses 5 files with distinct error handling responsibilities:

1. **`abc.py`** - Defines return type (discriminated union for operations that can fail)
2. **`real.py`** - Catches errors and converts to discriminated union
3. **`fake.py`** - Returns error discriminant based on constructor params (NO try/except)
4. **`dry_run.py`** - Returns success discriminant (NO try/except)
5. **`printing.py`** - Logs and delegates (NO try/except)

## Error Boundary Responsibilities

### real.py: The Error Boundary

**Purpose**: Catch subprocess and system errors, convert to discriminated union

```python
class RealGitBranchOps(GitBranchOps):
    def create_branch(self, *, name: str, start_point: str) -> CreateBranchResult:
        try:
            result = run_subprocess(
                ["git", "branch", name, start_point],
                cwd=self._cwd,
                capture_output=True,
            )
            if result.returncode != 0:
                return CreateBranchResult(
                    type="branch_already_exists",
                    branch_name=name,
                )
            return CreateBranchResult(type="success", branch_name=name)
        except Exception as e:
            # Convert unexpected errors to discriminated union
            return CreateBranchResult(type="error", message=str(e))
```

**Key patterns:**

- Uses `try/except` to catch subprocess and system errors
- Checks return codes to distinguish expected failure modes
- Returns appropriate discriminant for each failure case
- Converts unexpected exceptions to generic error discriminant

### fake.py: Constructor-Driven Error Simulation

**Purpose**: Return error discriminants based on constructor params, NO exception handling

```python
@dataclass(frozen=True)
class FakeGitBranchOps(GitBranchOps):
    create_branch_error: CreateBranchResult | None = None

    def create_branch(self, *, name: str, start_point: str) -> CreateBranchResult:
        if self.create_branch_error is not None:
            return self.create_branch_error
        return CreateBranchResult(type="success", branch_name=name)
```

**Key patterns:**

- **NO try/except blocks** - fakes don't catch exceptions
- Error behavior configured via constructor params
- Returns discriminants directly based on params
- Enables test-driven error scenarios without subprocess overhead

### dry_run.py: Success Path Only

**Purpose**: Log and return success discriminant, NO error handling

```python
@dataclass(frozen=True)
class DryRunGitBranchOps(GitBranchOps):
    logger: DryRunLogger

    def create_branch(self, *, name: str, start_point: str) -> CreateBranchResult:
        self.logger.log(f"Would create branch: {name} from {start_point}")
        return CreateBranchResult(type="success", branch_name=name)
```

**Key patterns:**

- **NO try/except blocks** - dry-run always succeeds
- Always returns success discriminant
- Logs what would have been done
- Useful for validating command sequences without side effects

### printing.py: Delegator Only

**Purpose**: Log operations and delegate to wrapped implementation, NO error handling

```python
@dataclass(frozen=True)
class PrintingGitBranchOps(GitBranchOps):
    impl: GitBranchOps
    logger: Logger

    def create_branch(self, *, name: str, start_point: str) -> CreateBranchResult:
        self.logger.info(f"Creating branch: {name} from {start_point}")
        return self.impl.create_branch(name=name, start_point=start_point)
```

**Key patterns:**

- **NO try/except blocks** - just delegates
- Logs operations for debugging/audit trail
- Returns whatever the wrapped implementation returns
- Transparent wrapper pattern

## When try/except IS Appropriate in Gateways

The real implementation uses `try/except` in two scenarios:

1. **Multiple failure modes**: When an operation can fail in several ways (e.g., branch already exists vs. invalid start point vs. permission error)
2. **Atomic operations**: When you need to catch unexpected errors and convert them to discriminated union error discriminants

## When try/except is NOT Appropriate in Gateways

- **Fake implementations**: Use constructor params to simulate errors
- **Dry-run implementations**: Always return success, never fail
- **Printing implementations**: Just delegate, don't intercept errors

## Testing Error Scenarios

Use fake constructor params to simulate errors in tests:

```python
def test_create_branch_already_exists():
    fake = FakeGitBranchOps(
        create_branch_error=CreateBranchResult(
            type="branch_already_exists",
            branch_name="feature",
        )
    )
    result = fake.create_branch(name="feature", start_point="main")
    assert result.type == "branch_already_exists"
```

This avoids subprocess overhead and makes tests fast and deterministic.

## Related Patterns

- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-file checklist
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - "Does the caller continue?" framing
- [Subprocess Wrappers](subprocess-wrappers.md) - Subprocess execution patterns
- [Fake-Driven Testing](../testing/fake-driven-testing.md) - 5-layer test architecture

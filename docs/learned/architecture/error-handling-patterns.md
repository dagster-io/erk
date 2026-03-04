---
title: Error Handling Patterns
read_when:
  - "implementing error handling in exec scripts"
  - "deciding between fail-fast and best-effort patterns"
  - "handling GitHub API errors gracefully"
tripwires:
  - action: "swallowing errors silently in a deterministic code path"
    warning: "Never suppress errors deterministically. Use best-effort (catch + log warning) only for truly optional operations. Use error-first (check + fail with remediation) for required operations."
    score: 5
  - action: "writing a try-except block that wraps multiple independent operations"
    warning: "Minimal exception scope: each try block should wrap only the single operation that can raise the caught exception. Split into separate try-except blocks with early returns. Broader scope is only acceptable when statements form an atomic unit (same message and recovery regardless of which line raises). See dignified-python references/exception-handling.md."
    score: 4
---

# Error Handling Patterns

Erk uses three distinct error handling strategies depending on the operation's criticality. These patterns apply specifically to exec scripts and gateway operations.

## Pattern 1: Best-Effort, Never-Block

For optional operations that should not prevent the main workflow from completing.

**When to use:** Lifecycle stage updates, telemetry, non-critical metadata writes.

**Pattern:** Catch the exception, log a warning, and continue.

```python
try:
    backend.update_metadata(repo_root, plan_id, metadata={"lifecycle_stage": "impl"})
except RuntimeError as e:
    # Best-effort: log and continue, don't block implementation
    click.echo(f"Warning: Failed to update lifecycle stage: {e}", err=True)
```

**Example:** `mark_impl_started.py` catches `RuntimeError` from GitHub API failures and returns a success=False result without raising, allowing the implementation to proceed.

## Pattern 2: Error-First Validation

For operations where failure should stop execution immediately with actionable remediation.

**When to use:** Pre-flight checks, resource validation, configuration verification.

**Pattern:** Check all preconditions before attempting the operation. Fail with a clear error message that includes remediation steps.

```python
# Check conditions first
if not plan_file.exists():
    click.echo(f"Error: Plan file not found: {plan_file}")
    click.echo("Remediation: Run 'erk exec setup-impl --issue <N>' first")
    raise SystemExit(1)

# All checks passed, proceed with operation
```

**Example:** `plan_save.py` validates plan content, checks for duplicate saves (session idempotency), and verifies GitHub authentication before making any API calls.

## Pattern 3: Silent Fallback Prohibition

Deterministic error suppression is forbidden. If an operation fails in a predictable way, it should either:

1. **Fail loudly** with a clear error message
2. **Return an explicit sentinel value** (not silently return None)

**Anti-pattern:**

```python
# WRONG: Silent fallback
def get_plan_number():
    try:
        return int(read_file())
    except (FileNotFoundError, ValueError):
        return None  # Caller has no idea why this is None
```

**Correct pattern:**

```python
# RIGHT: Explicit sentinel or error
def get_plan_number() -> int | PlanNotFound:
    if not plan_file.exists():
        return PlanNotFound(reason="file_missing")
    content = plan_file.read_text()
    if not content.strip().isdigit():
        return PlanNotFound(reason="invalid_content")
    return int(content)
```

## Inference Hoisting

LLM inference calls are moved to the earliest possible point in the workflow (the skill layer), not buried in exec scripts. This prevents nested LLM calls that can deadlock in Claude Code sessions.

See [Inference Hoisting](inference-hoisting.md) for the full pattern.

## Related Topics

- [Inference Hoisting](inference-hoisting.md) - LLM call placement strategy
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Result type patterns
- [Command Composition](command-composition.md) - How orchestrator commands aggregate errors

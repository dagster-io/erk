---
title: Fail-Open Pattern
last_audited: "2026-02-07"
audit_result: regenerated
read_when:
  - "implementing cleanup operations"
  - "designing resilient workflows"
  - "handling optional or non-critical operations"
tripwires:
  - action: "implementing a cleanup operation that modifies metadata based on external API success"
    warning: "Use fail-open pattern. If critical step fails, do NOT execute dependent steps that modify persistent state."
---

# Fail-Open Pattern

The fail-open pattern allows non-critical operations to fail without blocking the main workflow. The key insight: **asymmetric error handling preserves metadata consistency** by only updating persistent state after critical operations succeed.

## Why Fail-Open Exists

Erk workflows frequently involve external APIs (GitHub, git) that can fail due to rate limits, network errors, or resource state. When auxiliary operations fail, we face a choice:

- **Fail-closed**: Abort the entire workflow, forcing users to retry
- **Fail-open**: Log warnings and continue, letting the main operation succeed

Fail-open optimizes for user experience (don't block on cosmetic failures) while maintaining correctness through careful dependency analysis.

## Pattern vs Alternatives

| Pattern         | Behavior on Failure    | Use Case                                                     |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| **Fail-open**   | Log warning, continue  | Non-critical cleanup, external API calls, optional features  |
| **Fail-closed** | Raise exception, abort | Critical operations, data integrity requirements             |
| **Fail-fast**   | Validate early, abort  | Precondition checking, input validation before any mutations |

**The decision test**: If this step fails, does continuing create data inconsistency or confuse users? If no, fail-open. If yes, fail-closed.

## Core Implementation Pattern

### Step Classification

Categorize each step in your workflow:

1. **Cosmetic** - Nice-to-have (comments, notifications). Fail: log warning, continue.
2. **Critical** - Must succeed for correctness (API mutations, state changes). Fail: log warning, return early.
3. **Dependent** - Only valid after critical step succeeds (metadata updates). Execute only if critical succeeded.

### Asymmetric Handling for Metadata Consistency

The key insight: **metadata should only reflect successfully completed critical operations**.

**WRONG** — metadata inconsistency:

```python
# Close PR (might fail)
try:
    ctx.github.close_pr(repo_root, pr_number)
except RuntimeError:
    user_output("Warning: Could not close PR")
    # WRONG: Continue anyway

# Clear metadata (always executes)
clear_pr_metadata(issue_number)  # ← Metadata says "no PR" but PR is still open!
```

**CORRECT** — asymmetric early return:

```python
# Close PR (critical step)
try:
    ctx.github.close_pr(repo_root, pr_number)
except RuntimeError:
    user_output("Warning: Could not close PR")
    return None  # ← Do NOT execute dependent metadata update

# Clear metadata (dependent step - only executes if we reach this line)
clear_pr_metadata(issue_number)
```

If the metadata update itself fails after a successful PR close, that's tolerable—the PR is already closed, the inconsistency is minor.

## Canonical Example

<!-- Source: src/erk/cli/commands/review_pr_cleanup.py, cleanup_review_pr -->

See `cleanup_review_pr()` in `src/erk/cli/commands/review_pr_cleanup.py`.

**Context**: When closing or landing a plan, we optionally close its review PR. The review PR is non-critical to the main operation, but metadata consistency matters.

**Three-step pattern**:

1. Add comment explaining closure (cosmetic) — catch, log, continue
2. Close the PR (critical) — catch, log, **return None** to prevent metadata update
3. Clear `review_pr` field (dependent) — only executes if step 2 succeeded

**Why this works**: If the PR close fails, `review_pr` remains in metadata, allowing retry later. If the PR close succeeds but metadata update fails, the inconsistency is tolerable—the PR is already closed.

## Implementation Checklist

1. **Identify critical steps** — which operations must succeed?
   - Does it modify external state (API, database, filesystem)?
   - Would continuing after failure cause data inconsistency?
   - Is the operation reversible if it fails?

2. **Structure error handling asymmetrically**:

   ```python
   # Non-critical: catch, log, continue
   try:
       optional_operation()
   except Exception:
       user_output("Warning: Optional operation failed")
       # Fall through to next step

   # Critical: catch, log, return
   try:
       critical_operation()
   except Exception:
       user_output("Warning: Critical operation failed")
       return None  # ← Prevent dependent steps

   # Dependent: only executes if critical succeeded
   update_metadata()
   ```

3. **Document fail-open behavior** — docstring should state:
   - "This function is fail-open: failures are logged as warnings, not exceptions"
   - Which steps are critical vs optional
   - What the return value indicates (e.g., `None` = critical step failed)

4. **Use return values, not boolean flags** — return `None` on critical failure, actual result on success. Avoid `success: bool` flags that require checking.

## Defense-in-Depth: Two-Layer Pattern

For complex workflows involving multiple failure modes, combine fail-open with **root cause recovery**.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, _get_pr_for_plan_direct -->

**Example**: The `trigger-async-learn` command needs PR review comments. See `_get_pr_for_plan_direct()` in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` starting at line 212.

**Two layers**:

1. **Layer 1: Lenient handler** — returns `None` on ANY failure (missing data, API errors, not found). No exceptions, no error messages. Pure gateway logic.

2. **Layer 2: Root cause recovery** — caller inspects `None` and decides what to do:

   ```python
   pr_info = _get_pr_for_plan_direct(...)

   if pr_info is None:
       click.echo("No PR found for plan, skipping review comments", err=True)
       review_comments = None  # Continue without PR data
   else:
       pr_number = pr_info["pr_number"]
       review_comments = fetch_review_comments(repo_root, pr_number)

   # Workflow continues with or without review comments
   ```

**Why two layers**:

- **Lenient handler isolates failure modes** — all lookup failures return `None` consistently
- **Root cause recovery provides context** — caller explains WHY there's no PR info
- **Graceful degradation** — workflow succeeds without optional data
- **Future-proof** — if we add recovery logic later, only Layer 1 changes

### When to Use Two-Layer Pattern

Use two layers when:

- Multiple failure modes exist (missing data vs API error vs not found)
- Caller needs to explain failures differently based on context
- Same operation is critical in one context, optional in another

**Example**: PR lookup for the same plan issue:

| Context          | Critical? | Failure Handling      | Rationale                              |
| ---------------- | --------- | --------------------- | -------------------------------------- |
| User CLI command | Yes       | Error exit            | User needs immediate feedback          |
| Async background | No        | Log warning, continue | Review comments are optional for learn |
| Pre-flight check | Yes       | Abort early           | Prevent invalid workflow trigger       |

The same gateway function (`_get_pr_for_plan_direct`) returns `None` in all cases. The **caller** decides whether `None` is acceptable.

## Real-World Usage

### erk plan close

- Close plan issue (critical, fail-closed)
- Cleanup review PR (optional, fail-open) ← `cleanup_review_pr()`
- Update metadata (critical, fail-closed)

If review PR cleanup fails, plan close still succeeds. Users can manually close the review PR later.

### erk land

- Merge PR (critical, fail-closed)
- Delete worktree (critical, fail-closed)
- Cleanup review PR (optional, fail-open) ← `cleanup_review_pr()`

If review PR cleanup fails, land still succeeds. The PR is merged and worktree is deleted—mission accomplished.

Both commands call the same fail-open `cleanup_review_pr()` function, demonstrating reuse of the pattern.

## Benefits

1. **Resilience** — main workflows succeed even when auxiliary operations fail
2. **User experience** — users aren't blocked by cosmetic failures (rate limits, transient errors)
3. **Debuggability** — warnings indicate what failed without hiding the issue
4. **Idempotency** — failed operations can be retried later (cleanup review PR, add comment)
5. **Metadata consistency** — asymmetric handling prevents corrupted state

## When to Use Fail-Closed Instead

Use fail-closed (raise exception) when:

**Data integrity is critical**:

- Financial transactions (debit/credit must both succeed or both fail)
- Account creation (user needs immediate feedback on validation failures)
- Database constraints (foreign key violations should abort)

**Silent failure would confuse users**:

- User explicitly requested the operation
- Operation creates irreversible state
- Failure indicates a bug, not transient error

**Correctness requires all steps**:

- Multi-step atomic operations (git commit + push)
- Configuration validation (invalid config should abort startup)

## When to Use Fail-Fast Instead

Use fail-fast (validate before mutations) when:

**Preconditions can be checked upfront**:

- Validate `--up` flag requires child branches BEFORE merging PR
- Check file exists BEFORE processing it
- Verify network connectivity BEFORE starting long operation

**Partial execution is worse than no execution**:

- Don't delete half the worktrees if cleanup fails midway
- Don't modify half the metadata blocks if parsing fails

**Key difference**: Fail-fast validates BEFORE any state changes. Fail-open catches failures DURING execution and decides whether to continue.

## Related Documentation

- [Branch Name Inference](../planning/branch-name-inference.md) - Recovery mechanism for missing branch_name
- [Erk Architecture Patterns](erk-architecture.md) - Fail-fast validation pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Type-safe error handling
- [LBYL Gateway Pattern](lbyl-gateway-pattern.md) - Precondition checking pattern

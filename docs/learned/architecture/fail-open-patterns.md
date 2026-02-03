---
title: Fail-Open Pattern
read_when:
  - "implementing cleanup operations"
  - "designing resilient workflows"
  - "handling optional or non-critical operations"
tripwires:
  - action: "implementing a cleanup operation that modifies metadata based on external API success"
    warning: "Use fail-open pattern. If critical step fails, do NOT execute dependent steps that modify persistent state."
---

# Fail-Open Pattern

The fail-open pattern allows non-critical operations to fail without blocking the main workflow, while preserving correctness through careful dependency analysis.

## Pattern Definition

**Fail-open:** A system that continues operating when a non-critical component fails, logging warnings instead of propagating exceptions.

**Key characteristics:**

1. **Critical vs non-critical distinction** - Identify which steps MUST succeed vs which are optional
2. **Asymmetric failure handling** - Critical failures return early, non-critical failures log warnings
3. **Metadata consistency** - Only update persistent state after critical operations succeed
4. **Graceful degradation** - Main workflow completes successfully even if optional steps fail

## When to Use

Use fail-open pattern when:

- **Non-critical operations** - Step is optional or cosmetic (logging, notifications, cleanup)
- **External dependencies** - Failure is outside your control (API rate limits, network errors)
- **Resilience required** - Main workflow must succeed even if auxiliary operations fail
- **Idempotent cleanup** - Operation can be retried later without harm

**Do NOT use fail-open when:**

- Operation is critical to correctness
- Failure indicates data corruption or invariant violation
- Silent failure would confuse users or hide bugs

## Pattern vs Alternatives

| Pattern         | Behavior on Failure    | Use Case                                                     |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| **Fail-open**   | Log warning, continue  | Non-critical cleanup, external API calls, optional features  |
| **Fail-closed** | Raise exception, abort | Critical operations, data integrity requirements             |
| **Fail-fast**   | Validate early, abort  | Precondition checking, input validation before any mutations |

## Canonical Example: cleanup_review_pr()

The `cleanup_review_pr()` function in `src/erk/cli/commands/review_pr_cleanup.py` demonstrates the fail-open pattern:

**Context:** When a plan is closed or landed, the associated review PR should be closed and metadata should be cleared. But closing the review PR is not critical to the main operation (closing the plan).

**Implementation:**

```python
def cleanup_review_pr(
    ctx: ErkContext,
    *,
    repo_root: Path,
    issue_number: int,
    reason: str,
) -> int | None:
    """Close a plan's review PR and clear its metadata.

    This function is fail-open: if any step fails, the main operation
    (plan close or land) still succeeds.
    """
    # LBYL checks (early return if no review PR exists)
    if not ctx.issues.issue_exists(repo_root, issue_number):
        return None

    issue = ctx.issues.get_issue(repo_root, issue_number)
    block = find_metadata_block(issue.body, "plan-header")
    if block is None or block.data.get("review_pr") is None:
        return None

    review_pr = block.data["review_pr"]

    # Step 1: Add comment (COSMETIC - fail-open)
    try:
        ctx.issues.add_comment(repo_root, review_pr, comment_body)
    except RuntimeError:
        user_output(f"Warning: Could not add comment to review PR #{review_pr}")
        # Continue anyway - comment is cosmetic

    # Step 2: Close PR (CRITICAL - fail-open with early return)
    try:
        ctx.github.close_pr(repo_root, review_pr)
    except RuntimeError:
        user_output(f"Warning: Could not close review PR #{review_pr}")
        # CRITICAL: Do NOT clear metadata if close fails
        return None

    # Step 3: Clear metadata (DEPENDENT - only after close succeeds)
    try:
        updated_body = clear_plan_header_review_pr(issue.body)
        ctx.issues.update_issue_body(repo_root, issue_number, updated_body)
    except (ValueError, RuntimeError):
        user_output(f"Warning: Could not clear review PR metadata for issue #{issue_number}")
        # Metadata update failed, but PR is closed - acceptable

    user_output(f"Closed review PR #{review_pr}")
    return review_pr
```

**Failure handling breakdown:**

| Step           | Type      | Failure Behavior         | Rationale                                             |
| -------------- | --------- | ------------------------ | ----------------------------------------------------- |
| Add comment    | Cosmetic  | Log warning, continue    | Comment is nice-to-have, not required                 |
| Close PR       | Critical  | Log warning, return None | Metadata should only be cleared if PR actually closed |
| Clear metadata | Dependent | Log warning, continue    | PR is closed, metadata inconsistency is tolerable     |

**Key insight:** Metadata consistency is preserved by asymmetric handling:

- If PR close **fails** → Metadata NOT cleared (review_pr remains, can retry later)
- If PR close **succeeds** → Metadata cleared (even if update fails, PR is already closed)

## Implementation Pattern

### Step 1: Identify Critical Steps

**Critical step:** A step whose failure means the entire operation should abort or return a sentinel value.

**Questions to ask:**

1. Does this step modify external state (API, database, filesystem)?
2. Is the operation reversible if it fails?
3. Would continuing after failure cause data inconsistency?

**Example:** In `cleanup_review_pr()`, closing the PR is critical because:

- It modifies GitHub state (PR is closed)
- Metadata should only be cleared if PR is actually closed
- Continuing after close failure would create inconsistency (metadata says "no review PR" but PR is still open)

### Step 2: Implement Asymmetric Error Handling

**Pattern:**

```python
# Non-critical step - log warning, continue
try:
    optional_operation()
except Exception:
    user_output("Warning: Optional operation failed")
    # Continue to next step

# Critical step - log warning, return early
try:
    critical_operation()
except Exception:
    user_output("Warning: Critical operation failed")
    return None  # Do NOT continue to dependent steps

# Dependent step - only executes if critical step succeeded
dependent_operation()
```

### Step 3: Document Fail-Open Semantics

Add a docstring explaining:

1. **Fail-open behavior** - "This function is fail-open: failures are logged as warnings, not exceptions"
2. **Critical vs non-critical** - Which steps must succeed vs which are optional
3. **Return value** - What does `None` mean? What does non-None mean?

**Example:**

```python
def cleanup_review_pr(...) -> int | None:
    """Close a plan's review PR and clear its metadata.

    This function is fail-open: if any step fails, the main operation
    (plan close or land) still succeeds. Warnings are logged but exceptions
    are not propagated.

    Returns:
        The review PR number if closed, None otherwise
    """
```

### Step 4: Add Tripwire to Prevent Misuse

If this is a general pattern in your codebase, add a tripwire to docs/learned/architecture/tripwires.md:

```yaml
- action: "implementing a cleanup operation that modifies metadata based on external API success"
  warning: "Use fail-open pattern. If critical step fails, do NOT execute dependent steps that modify persistent state."
```

## When to Use Fail-Closed Instead

Use fail-closed (raise exception) when:

**Data integrity is critical:**

```python
def transfer_money(from_account: int, to_account: int, amount: float) -> None:
    """Transfer money between accounts.

    Fail-closed: any failure aborts the entire operation.
    """
    # CRITICAL: Must succeed or abort
    debit(from_account, amount)  # Raises on failure
    credit(to_account, amount)    # Raises on failure
```

**User needs to know about failure:**

```python
def create_user(email: str, password: str) -> User:
    """Create a new user account.

    Fail-closed: user needs immediate feedback if creation fails.
    """
    user = User(email=email)
    user.set_password(password)  # Raises on weak password
    save_to_database(user)        # Raises on constraint violation
    return user
```

## When to Use Fail-Fast Instead

Use fail-fast (validate before mutations) when:

**Preconditions can be checked upfront:**

```python
def land_pr(ctx: ErkContext, *, up: bool = False) -> None:
    """Land current branch's PR.

    Fail-fast: validate --up preconditions BEFORE merging PR.
    """
    # FAIL-FAST: Validate --up preconditions before any mutations
    if up:
        child_branches = ctx.graphite.get_child_branches(current_branch)
        if not child_branches:
            raise ValueError("--up requires child branches to navigate upstack")

    # Now safe to proceed with mutations (PR merge, worktree delete)
    merge_pr(ctx, pr_number)
    delete_worktree(ctx, worktree_path)

    # Navigate upstack if requested
    if up:
        checkout_branch(ctx, child_branches[0])
```

**Key difference:** Fail-fast validates BEFORE any state changes, preventing partial mutations.

## Real-World Usage in Erk

### erk plan close

**Workflow:**

1. Close plan issue (CRITICAL)
2. Cleanup review PR (OPTIONAL - fail-open)
3. Update metadata (CRITICAL)

**Implementation:**

```python
def close_plan_issue(issue_number: int) -> None:
    # Step 1: Close the plan issue (CRITICAL - fail-closed)
    ctx.issues.close_issue(repo_root, issue_number)

    # Step 2: Cleanup review PR (OPTIONAL - fail-open)
    cleanup_review_pr(ctx, repo_root=repo_root, issue_number=issue_number, reason="plan closed")
    # If this fails, plan close still succeeds

    # Step 3: Update metadata (CRITICAL - fail-closed)
    update_plan_metadata(issue_number, status="closed")
```

### erk land

**Workflow:**

1. Merge PR (CRITICAL)
2. Delete worktree (CRITICAL)
3. Cleanup review PR (OPTIONAL - fail-open)

**Implementation:**

```python
def land_pr(ctx: ErkContext) -> None:
    # Step 1: Merge PR (CRITICAL - fail-closed)
    merge_result = ctx.github.merge_pr(repo_root, pr_number)

    # Step 2: Delete worktree (CRITICAL - fail-closed)
    delete_worktree(ctx, worktree_path)

    # Step 3: Cleanup review PR (OPTIONAL - fail-open)
    cleanup_review_pr(ctx, repo_root=repo_root, issue_number=issue_number, reason="PR landed")
    # If this fails, land still succeeds
```

**Key insight:** Both commands call `cleanup_review_pr()` with fail-open semantics, allowing the main operation to succeed even if cleanup fails.

## Benefits

1. **Resilience** - Main workflows succeed even when auxiliary operations fail
2. **User experience** - Users aren't blocked by non-critical failures
3. **Debuggability** - Warnings indicate what failed without hiding the issue
4. **Idempotency** - Failed cleanup operations can be retried later
5. **Metadata consistency** - Careful dependency ordering prevents state corruption

## Defense-in-Depth Example: trigger-async-learn

The `trigger-async-learn` command demonstrates a **two-layer defense-in-depth** approach combining fail-open with root cause recovery:

### The Problem

When triggering async learn for a plan, we need the associated PR number to fetch review comments. But:

1. **branch_name might be missing** - If impl-signal never ran or failed
2. **PR lookup might fail** - Network error, branch doesn't have a PR yet
3. **Review comments are optional** - Learn can succeed without them

### Two-Layer Solution

**Layer 1: Lenient Handler** (`_get_pr_for_plan_direct`)

See `_get_pr_for_plan_direct()` in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:212-257`.

```python
# Signature and return type (see source for full implementation):
def _get_pr_for_plan_direct(
    *, github_issues, github, repo_root: Path, issue_number: int,
) -> dict[str, object] | None:
    # Returns None on ANY failure: missing issue, metadata, branch, or PR
```

**Key characteristics:**

- Returns `None` on ANY failure (missing data, API errors, not found)
- No exceptions raised
- No error messages printed
- Caller decides how to handle None

**Layer 2: Root Cause Recovery**

The caller (trigger-async-learn main function) handles the None case gracefully:

```python
def trigger_async_learn_main(issue_number: int) -> None:
    # Try to get PR information (fail-open)
    pr_info = _get_pr_for_plan_direct(
        github_issues=ctx.issues,
        github=ctx.github,
        repo_root=repo_root,
        issue_number=issue_number,
    )

    if pr_info is None:
        # No PR found - that's OK, just skip review comments
        click.echo("No PR found for plan, skipping review comments", err=True)
        review_comments = None
    else:
        # PR found - fetch review comments
        pr_number = pr_info["pr_number"]
        review_comments = fetch_review_comments(repo_root, pr_number)

    # Continue with learn workflow (with or without review comments)
    upload_materials(sessions, review_comments)
    trigger_workflow(...)
```

### Defense-in-Depth Benefits

1. **Lenient handler isolates failure modes** - All PR lookup failures return None consistently
2. **Root cause recovery provides context** - Caller knows WHY there's no PR info
3. **Graceful degradation** - Learn succeeds without review comments
4. **Future-proof** - If we add branch_name inference later (like get_pr_for_plan.py), only Layer 1 changes

### Comparison with get_pr_for_plan.py

The `get_pr_for_plan.py` script has **recovery logic** for missing branch_name (pattern matching against current branch). But `trigger-async-learn` intentionally does NOT:

| Aspect               | get_pr_for_plan.py                   | trigger-async-learn                     |
| -------------------- | ------------------------------------ | --------------------------------------- |
| **Context**          | User is ON the branch right now      | Running from GitHub Actions (no branch) |
| **branch_name=None** | Try to infer from current git branch | Return None (no recovery)               |
| **No PR found**      | Error - user needs to know           | OK - review comments are optional       |
| **Failure mode**     | Fail-closed (error exit)             | Fail-open (continue without PR)         |

This demonstrates that fail-open vs fail-closed is **context-dependent** - the same operation (PR lookup) can be critical in one context and optional in another.

## Related Documentation

- [Branch Name Inference](../planning/branch-name-inference.md) - Recovery mechanism for missing branch_name
- [Erk Architecture Patterns](erk-architecture.md) - Fail-fast validation pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Type-safe error handling
- [LBYL Gateway Pattern](lbyl-gateway-pattern.md) - Precondition checking pattern

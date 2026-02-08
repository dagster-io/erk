---
title: GitHub Commit Indexing Timing
read_when:
  - "working with GitHub commit status API"
  - "debugging 422 'No commit found for SHA' errors"
  - "implementing CI verification workflows"
tripwires:
  - action: "calling create_commit_status() immediately after git push"
    warning: "GitHub's commit indexing has a race condition. Commits may not be immediately available for status updates after push. Use execute_gh_command_with_retry() wrapper, not direct subprocess calls."
---

# GitHub Commit Indexing Timing

## The Problem: Eventually Consistent Commit Indexing

GitHub's commit indexing is **eventually consistent**. After `git push`, there's a window (milliseconds to seconds) where:

1. The commit exists in the repository
2. Git commands see the commit locally
3. GitHub's database has NOT indexed the commit yet
4. Status API calls return 422: `{"message": "No commit found for SHA"}`

This is not a bug — it's an architectural property of distributed systems. The fix is retry logic, not faster pushes or API delays.

## Why This Matters

**Symptom:** CI verification workflows that push commits and immediately create status checks fail intermittently with "No commit found".

**Root cause:** The status API call races against GitHub's indexing pipeline.

**Impact:** Without retry logic, automation that does push → status in quick succession reports false failures.

## The Solution: Use execute_gh_command_with_retry()

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/parsing.py, execute_gh_command_with_retry -->

See `execute_gh_command_with_retry()` in `packages/erk-shared/src/erk_shared/gateway/github/parsing.py`.

**Key characteristics:**
- Wraps `run_subprocess_with_context()` with transient error detection
- Checks error messages against `TRANSIENT_ERROR_PATTERNS`
- Uses exponential backoff (default: 2s, 4s, 8s, 16s, 32s)
- Accepts injectable `time_impl` for testability

## Anti-Pattern: Direct Subprocess Calls Without Retry

❌ **WRONG — No retry logic:**

```python
def create_commit_status(...) -> bool:
    cmd = ["gh", "api", f"repos/{repo}/statuses/{sha}", ...]
    try:
        run_subprocess_with_context(cmd=cmd, ...)
        return True
    except RuntimeError:
        return False  # Treats transient error as permanent failure
```

This was the state after PR #6100 — a refactor from bash to Python that accidentally dropped the original retry logic.

## Current State: Retry Not Applied to Commit Status

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.create_commit_status -->

See `RealGitHub.create_commit_status()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py:2113-2146`.

**Current implementation:** Calls `run_subprocess_with_context()` directly — NO retry logic.

**Missing pattern:** Should be added to `TRANSIENT_ERROR_PATTERNS`:

```python
TRANSIENT_ERROR_PATTERNS = (
    # ... existing patterns ...
    "no commit found for sha",  # GitHub indexing race condition
)
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/transient_errors.py, TRANSIENT_ERROR_PATTERNS -->

See `TRANSIENT_ERROR_PATTERNS` in `packages/erk-shared/src/erk_shared/gateway/github/transient_errors.py` for the current list of retry-worthy errors.

## Historical Context: The Regression

### Timeline

1. **PR #6089 (commit 36846ee8):** Bash script in `.github/workflows/ci.yml` added retry logic with exponential backoff for commit status reporting
2. **PR #6100 (commit a1a5280d, 17 minutes later):** Extracted bash script to `erk exec ci-verify-autofix` Python command
3. **Regression:** The retry logic did NOT carry forward into the Python implementation

### Why the Regression Happened

The original fix was bash code with inline retry loops. When refactoring to Python, the visible surface was the gh command itself, not the retry wrapper around it. The retry logic lived in a bash function, not as a reusable abstraction.

**Lesson:** Retries belong in the gateway layer (as wrappers like `execute_gh_command_with_retry()`), not in call sites. Otherwise, every refactor risks dropping them.

## Decision Table: When to Use Retry Wrapper

| Scenario | Use execute_gh_command_with_retry? | Why |
|----------|-----------------------------------|-----|
| Reading data (GET) | Yes | Network errors are transient, reads are idempotent |
| Creating resources (POST) | Yes, with idempotency | Retry is safe if operation has idempotency key or natural deduplication |
| Status updates after push | **Yes** | This doc's exact use case — GitHub needs time to index |
| Deleting resources (DELETE) | Maybe | Depends on whether 404 on retry is acceptable |

## Related Documentation

- [GitHub API Retry Mechanism](../architecture/github-api-retry-mechanism.md) — Retry infrastructure and patterns
- [Subprocess Wrappers](../architecture/subprocess-wrappers.md) — When to use subprocess wrappers vs direct calls

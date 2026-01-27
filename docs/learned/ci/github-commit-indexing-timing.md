---
title: GitHub Commit Indexing Timing
read_when:
  - "working with GitHub commit status API"
  - "debugging 422 'No commit found for SHA' errors"
  - "implementing CI verification workflows"
tripwires:
  - action: "calling create_commit_status() immediately after git push"
    warning: "GitHub's commit indexing has a race condition. Commits may not be immediately available for status updates after push. Consider adding retry logic with exponential backoff."
---

# GitHub Commit Indexing Timing

## The Race Condition

When you push a commit to GitHub and immediately try to create a commit status via the GitHub API, the operation may fail with a 422 error:

```
HTTP 422: Validation Failed
{"message": "No commit found for SHA"}
```

This happens because GitHub's commit indexing is **eventually consistent**. After a `git push`, there's a brief window (typically milliseconds to seconds) where:

1. The commit exists in the repository
2. The commit is visible via `git log`
3. The commit is NOT yet indexed in GitHub's database
4. Status API calls fail with "No commit found"

## Historical Context: The Regression

### Original Fix (PR #6089, commit 36846ee8)

The autofix verification workflow in `.github/workflows/ci.yml` originally had retry logic to handle this race condition:

```bash
report_status() {
  local name="$1"
  local state="$2"
  local desc="$3"
  local max_retries=5
  local retry_delay=2

  for i in $(seq 1 $max_retries); do
    if gh api repos/${{ github.repository }}/statuses/$current_sha \
      -f state="$state" \
      -f context="ci / $name (autofix-verified)" \
      -f description="$desc" 2>/dev/null; then
      return 0
    fi

    if [ $i -lt $max_retries ]; then
      echo "Status report failed (attempt $i/$max_retries), retrying in ${retry_delay}s..."
      sleep $retry_delay
      retry_delay=$((retry_delay * 2))
    fi
  done

  echo "Warning: Failed to report status for $name after $max_retries attempts"
  return 0  # Don't fail the workflow for status reporting issues
}
```

This implementation used exponential backoff:

- Initial delay: 2 seconds
- Max retries: 5 attempts
- Delay growth: 2x each retry (2s, 4s, 8s, 16s)

### The Refactor That Removed Retry Logic (PR #6100, commit a1a5280d)

PR #6100 extracted CI verification logic from the bash shell script into a Python command: `erk exec ci-verify-autofix`. During this refactor (17 minutes after the original fix), the retry logic was **not carried forward** into the Python implementation.

Current implementation in `packages/erk-shared/src/erk_shared/gateway/github/real.py`:

```python
def create_commit_status(
    self,
    *,
    repo: str,
    sha: str,
    state: str,
    context: str,
    description: str,
) -> bool:
    """Create a commit status on GitHub via REST API."""
    cmd = [
        "gh", "api", f"repos/{repo}/statuses/{sha}",
        "-f", f"state={state}",
        "-f", f"context={context}",
        "-f", f"description={description}",
    ]

    try:
        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"create commit status for {sha[:8]}",
        )
        return True
    except RuntimeError:
        return False
```

This implementation has **NO retry logic** - it makes a single attempt and returns False on failure.

## Current State

The `transient_errors.py` module defines patterns for retry-worthy errors, but it does NOT include the "No commit found for SHA" pattern:

```python
TRANSIENT_ERROR_PATTERNS = (
    "i/o timeout",
    "dial tcp",
    "connection refused",
    "could not connect",
    "network is unreachable",
    "connection reset",
    "connection timed out",
)
```

The commit indexing race condition is **not represented** in this list.

## Recommendations

To restore the original behavior and prevent spurious failures:

1. **Add retry pattern to `transient_errors.py`**:

   ```python
   TRANSIENT_ERROR_PATTERNS = (
       # ... existing patterns ...
       "no commit found for sha",
   )
   ```

2. **Wrap `create_commit_status()` with retry logic**:
   - Use `execute_gh_command_with_retry()` instead of direct `run_subprocess_with_context()`
   - Pass `time_impl` for testability (enables FakeTime in tests)
   - Follow the pattern from other retry-enabled GitHub operations

3. **Use exponential backoff parameters matching the original**:
   - Max retries: 5 attempts
   - Initial delay: 2 seconds
   - Exponential growth: 2x

## Why This Matters

Without retry logic, CI verification workflows can report false failures when:

- Autofix commits are pushed and immediately verified
- Remote workflows push commits and create status checks
- Any automation that does push + status in quick succession

The race condition is **transient** - waiting a few seconds almost always resolves it. Treating it as a permanent failure causes unnecessary noise and workflow failures.

## Related Documentation

- [GitHub API Retry Mechanism](../architecture/github-api-retry-mechanism.md) - Retry infrastructure
- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - API best practices
- [CI Verification Commands](../cli/ci-verification-commands.md) - ci-verify-autofix usage

# Add "unexpected end of JSON input" as transient error

## Context

`erk down -f -d` crashed when `gh api --method PATCH repos/{owner}/{repo}/pulls/8702 -f state=closed` returned exit code 1 with stderr `unexpected end of JSON input`. This is a transient GitHub API error (truncated response), but it's not in `TRANSIENT_ERROR_PATTERNS`, so the retry logic never fires and the command fails immediately.

The same command succeeds on retry — confirming it's transient.

## Plan

### 1. Add pattern to `TRANSIENT_ERROR_PATTERNS`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/transient_errors.py`

Add `"unexpected end of json input"` to the tuple (lowercase, matching the existing convention).

### 2. Add test

**File:** `packages/erk-shared/tests/unit/github/test_transient_errors.py`

Add a test following the existing pattern:

```python
def test_unexpected_end_of_json_input_detected() -> None:
    """Test that unexpected end of JSON input is detected as transient."""
    error = "unexpected end of JSON input"
    assert is_transient_error(error) is True
```

## Verification

- Run `pytest packages/erk-shared/tests/unit/github/test_transient_errors.py`
- Run `pytest packages/erk-shared/tests/unit/github/test_execute_gh_command_with_retry.py`

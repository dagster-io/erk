# Plan: Enhanced Debug Logging for gh Commands and GraphQL Queries

## Goal

Add comprehensive debug logging with timing for:
1. Every `gh` command execution
2. Every GraphQL query with full query content (multi-line)

## Current State

Two `execute_gh_command` functions exist:
- `erk_shared/subprocess_utils.py:98` - Has debug logging but no timing
- `erk_shared/github/parsing.py:11` - No debug logging at all (used by `real.py` for GraphQL)

GraphQL queries are built in `real.py` methods but never logged.

## Implementation Approach: Reusable Timing Utility

### Step 1: Create `debug_timing.py` module

**File:** `packages/erk-shared/src/erk_shared/debug_timing.py`

```python
"""Debug timing utilities for subprocess and API operations."""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def timed_operation(operation: str) -> Generator[None, None, None]:
    """Context manager that logs operation timing on completion.

    Args:
        operation: Human-readable description of the operation
    """
    start_time = time.perf_counter()
    logger.debug("Starting: %s", operation)
    try:
        yield
    finally:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.debug("Completed in %dms: %s", elapsed_ms, operation)


def log_graphql_query(query: str) -> None:
    """Log GraphQL query content for debugging (multi-line)."""
    logger.debug("GraphQL query:\n%s", query)
```

### Step 2: Add timing to `parsing.py:execute_gh_command`

**File:** `packages/erk-shared/src/erk_shared/github/parsing.py`

Add import and wrap the subprocess call:

```python
from erk_shared.debug_timing import timed_operation

def execute_gh_command(cmd: list[str], cwd: Path) -> str:
    cmd_str = " ".join(cmd)
    operation_context = f"execute gh command '{cmd_str}'"

    with timed_operation(f"gh: {cmd_str}"):
        result = run_subprocess_with_context(
            cmd,
            operation_context=operation_context,
            cwd=cwd,
        )

    return result.stdout
```

### Step 3: Add timing to `subprocess_utils.py:execute_gh_command`

**File:** `packages/erk-shared/src/erk_shared/subprocess_utils.py`

Wrap the existing subprocess call with timing:

```python
import time  # Add to imports

def execute_gh_command(cmd: list[str], cwd: Path) -> str:
    cmd_str = " ".join(cmd)
    logger.debug("Executing gh command: %s (cwd=%s)", cmd_str, cwd)
    start_time = time.perf_counter()  # ADD
    try:
        result = subprocess.run(...)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)  # ADD
        stdout_preview = result.stdout[:200] if result.stdout else "(empty)"
        logger.debug("gh command succeeded in %dms, stdout preview: %s", elapsed_ms, stdout_preview)  # MODIFY
        return result.stdout
    except subprocess.CalledProcessError as e:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)  # ADD
        logger.debug(
            "gh command failed in %dms: exit_code=%d, stdout=%s, stderr=%s",  # MODIFY
            elapsed_ms,
            e.returncode,
            e.stdout,
            e.stderr,
        )
        # ... rest unchanged
```

### Step 4: Add GraphQL query logging to `real.py`

**File:** `src/erk/core/github/real.py`

Add import and log queries before execution:

```python
from erk_shared.debug_timing import log_graphql_query

def _execute_batch_pr_query(self, query: str, repo_root: Path) -> dict[str, Any]:
    """Execute batched GraphQL query via gh CLI."""
    log_graphql_query(query)  # ADD
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    stdout = execute_gh_command(cmd, repo_root)
    return json.loads(stdout)
```

Also add `log_graphql_query()` calls to other GraphQL-executing methods:
- `get_prs_linked_to_issues()` (line ~855)
- `get_multiple_issue_comments()` in `issues/real.py`

### Step 5: Add unit tests

**File:** `tests/unit/test_debug_timing.py`

```python
import logging
import pytest
from erk_shared.debug_timing import log_graphql_query, timed_operation


def test_timed_operation_logs_start_and_completion(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        with timed_operation("test operation"):
            pass

    assert len(caplog.records) == 2
    assert "Starting: test operation" in caplog.records[0].message
    assert "Completed in" in caplog.records[1].message
    assert "test operation" in caplog.records[1].message


def test_log_graphql_query_preserves_multiline(caplog: pytest.LogCaptureFixture) -> None:
    query = "query {\n  repository {\n    name\n  }\n}"

    with caplog.at_level(logging.DEBUG):
        log_graphql_query(query)

    assert len(caplog.records) == 1
    assert "GraphQL query:" in caplog.records[0].message
    assert "repository" in caplog.records[0].message
```

## Expected Debug Output

With `--debug` flag:

```
erk_shared.debug_timing - DEBUG - Starting: gh: gh pr list --state all --json number,headRefName,url,state,isDraft,title
erk_shared.debug_timing - DEBUG - Completed in 342ms: gh: gh pr list --state all --json number,headRefName,url,state,isDraft,title
erk_shared.debug_timing - DEBUG - GraphQL query:
fragment PRCICheckFields on PullRequest {
  number
  title
  ...
}
erk_shared.debug_timing - DEBUG - Starting: gh: gh api graphql -f query=...
erk_shared.debug_timing - DEBUG - Completed in 567ms: gh: gh api graphql -f query=...
```

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/debug_timing.py` | NEW - timing utilities |
| `packages/erk-shared/src/erk_shared/github/parsing.py` | Add timing wrapper |
| `packages/erk-shared/src/erk_shared/subprocess_utils.py` | Add timing to existing logging |
| `src/erk/core/github/real.py` | Add GraphQL query logging |
| `packages/erk-shared/src/erk_shared/github/issues/real.py` | Add GraphQL query logging |
| `tests/unit/test_debug_timing.py` | NEW - unit tests |
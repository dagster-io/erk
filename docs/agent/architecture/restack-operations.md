---
title: Three-Phase Restack Architecture
read_when:
  - "implementing or modifying restack operations"
  - "understanding preflight/continue/finalize pattern"
  - "working with RestackPreflightSuccess/Error types"
  - "adding new three-phase operations"
---

# Three-Phase Restack Architecture

This document describes the three-phase architecture used for Graphite restack operations with automated conflict handling.

## Overview

The restack operation is split into three phases to enable automated conflict resolution loops:

```
┌─────────────────┐
│    Preflight    │──► Squash commits + attempt restack
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │Conflicts│──► No conflicts? Skip to Finalize
    └────┬────┘
         │ Yes
         ▼
┌─────────────────┐
│ Continue Loop   │◄──┐
│  - Resolve      │   │
│  - Stage        │   │ More conflicts?
│  - Continue     │───┘
└────────┬────────┘
         │ Complete
         ▼
┌─────────────────┐
│    Finalize     │──► Verify clean completion
└─────────────────┘
```

## Phase 1: Preflight

**Purpose:** Prepare branch and detect initial conflicts.

**Location:** `packages/erk-shared/src/erk_shared/integrations/gt/operations/restack_preflight.py`

**Steps:**

1. Squash all commits on current branch (via execute_squash)
2. Attempt `gt restack --no-interactive`
3. Check if rebase is in progress (conflicts detected)

**Return Types:**

```python
@dataclass(frozen=True)
class RestackPreflightSuccess:
    """Success result from restack preflight."""
    success: Literal[True]
    has_conflicts: bool
    conflicts: list[str]  # File paths with conflicts
    branch_name: str
    message: str

@dataclass(frozen=True)
class RestackPreflightError:
    """Error result from restack preflight."""
    success: Literal[False]
    error_type: RestackPreflightErrorType  # "squash_conflict", "squash_failed", etc.
    message: str
    details: dict[str, str]
```

**Decision Points:**

| Result                              | Action              |
| ----------------------------------- | ------------------- |
| `success=True, has_conflicts=False` | Skip to Finalize    |
| `success=True, has_conflicts=True`  | Enter Continue Loop |
| `success=False`                     | Report error, abort |

## Phase 2: Continue Loop

**Purpose:** Resolve conflicts and continue restack until completion.

**Location:** `packages/erk-shared/src/erk_shared/integrations/gt/operations/restack_continue.py`

**Steps:**

1. Stage resolved conflict files
2. Run `gt continue`
3. Check for new conflicts

**Return Types:**

```python
@dataclass(frozen=True)
class RestackContinueSuccess:
    """Success result from restack continue."""
    success: Literal[True]
    restack_complete: bool  # True if no more conflicts
    has_conflicts: bool
    conflicts: list[str]  # New conflict files
    branch_name: str
    message: str

@dataclass(frozen=True)
class RestackContinueError:
    """Error result from restack continue."""
    success: Literal[False]
    error_type: RestackContinueErrorType  # "stage_failed", "continue_failed"
    message: str
    details: dict[str, str]
```

**Loop Logic:**

```
While not complete:
    1. Resolve conflicts (semantic vs mechanical classification)
    2. Call execute_restack_continue(resolved_files)
    3. If restack_complete: exit loop
    4. If has_conflicts: continue with new conflicts list
    5. If error: report and abort
```

## Phase 3: Finalize

**Purpose:** Verify restack completed cleanly.

**Location:** `packages/erk-shared/src/erk_shared/integrations/gt/operations/restack_finalize.py`

**Steps:**

1. Verify no rebase is in progress
2. Verify working tree is clean

**Return Types:**

```python
@dataclass(frozen=True)
class RestackFinalizeSuccess:
    """Success result from restack finalize."""
    success: Literal[True]
    branch_name: str
    message: str

@dataclass(frozen=True)
class RestackFinalizeError:
    """Error result from restack finalize."""
    success: Literal[False]
    error_type: RestackFinalizeErrorType  # "rebase_still_in_progress", "dirty_working_tree"
    message: str
    details: dict[str, str]
```

## Error Types

All error types are defined in `packages/erk-shared/src/erk_shared/integrations/gt/types.py`:

**Preflight Errors:**

- `squash_conflict` - Conflicts during commit squashing
- `squash_failed` - Squash command failed
- `no_commits` - No commits to squash
- `restack_failed` - Restack command failed unexpectedly
- `not_in_repo` - Not in a git repository

**Continue Errors:**

- `stage_failed` - Failed to stage resolved files
- `continue_failed` - gt continue command failed

**Finalize Errors:**

- `rebase_still_in_progress` - Rebase not fully resolved
- `dirty_working_tree` - Uncommitted changes remain

## Integration with GtKit

All operations use dependency injection via `GtKit`:

```python
def execute_restack_preflight(
    ops: GtKit,  # Dependency injection
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[...]]
```

The `GtKit` protocol provides access to:

- `ops.git` - Git operations (get_current_branch, is_rebase_in_progress, etc.)
- `ops.graphite` - Graphite operations (restack, continue_restack)

This enables testing with `FakeGtKitOps` without real git/graphite commands.

## Testing Pattern

```python
def test_preflight_detects_conflicts() -> None:
    """Test preflight correctly identifies conflicts."""
    fake_git = FakeGit()
    fake_git.rebase_in_progress = True
    fake_git.conflicted_files = ["src/module.py"]

    fake_graphite = FakeGraphite()
    fake_ops = FakeGtKitOps(git=fake_git, graphite=fake_graphite)

    events = list(execute_restack_preflight(fake_ops, Path("/repo")))
    completion = events[-1]

    assert isinstance(completion, CompletionEvent)
    result = completion.result
    assert result.success is True
    assert result.has_conflicts is True
    assert result.conflicts == ["src/module.py"]


def test_continue_reports_completion() -> None:
    """Test continue correctly reports when restack is done."""
    fake_git = FakeGit()
    fake_git.rebase_in_progress = False  # Restack completed

    fake_ops = FakeGtKitOps(git=fake_git, graphite=FakeGraphite())

    events = list(execute_restack_continue(
        fake_ops,
        Path("/repo"),
        resolved_files=["src/module.py"],
    ))
    completion = events[-1]

    result = completion.result
    assert result.success is True
    assert result.restack_complete is True
```

## Event-Based Progress

All three operations use the event-based progress pattern:

```python
# Each operation yields progress, then completion
yield ProgressEvent("Squashing commits...")
# ... do work ...
yield ProgressEvent("Running gt restack...", style="info")
# ... check results ...
yield ProgressEvent(f"Found {len(conflicts)} conflict(s)", style="warning")
yield CompletionEvent(RestackPreflightSuccess(...))
```

See [Event-Based Progress Pattern](event-progress-pattern.md) for details.

## Complete Flow Example

```python
def auto_restack(ops: GtKit, cwd: Path) -> RestackResult:
    """Complete auto-restack with conflict resolution."""

    # Phase 1: Preflight
    for event in execute_restack_preflight(ops, cwd):
        if isinstance(event, CompletionEvent):
            preflight_result = event.result
            break

    if not preflight_result.success:
        return RestackResult(success=False, error=preflight_result.message)

    # Phase 2: Continue loop (if conflicts)
    while preflight_result.has_conflicts:
        resolved_files = resolve_conflicts(preflight_result.conflicts)

        for event in execute_restack_continue(ops, cwd, resolved_files):
            if isinstance(event, CompletionEvent):
                continue_result = event.result
                break

        if not continue_result.success:
            return RestackResult(success=False, error=continue_result.message)

        if continue_result.restack_complete:
            break

        preflight_result = continue_result  # Loop with new conflicts

    # Phase 3: Finalize
    for event in execute_restack_finalize(ops, cwd):
        if isinstance(event, CompletionEvent):
            finalize_result = event.result
            break

    return RestackResult(
        success=finalize_result.success,
        branch_name=finalize_result.branch_name,
    )
```

## Related Documentation

- [Event-Based Progress Pattern](event-progress-pattern.md) - Progress reporting pattern
- [Auto-Restack Command Usage](../erk/auto-restack.md) - User-facing workflow guide
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection context
- [Git and Graphite Edge Cases](git-graphite-quirks.md) - Catalog of surprising git/gt behaviors

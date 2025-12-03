# Plan: Unit Tests for GT Operations with Event Assertions

## Overview

Add comprehensive unit tests for the GT operations layer in `erk-shared` that assert against both the final result AND key events emitted during execution.

## Design Decisions

- **Test location**: Move `FakeGtKitOps` to `erk-shared` and create tests there (ops code lives in erk-shared)
- **Event assertions**: Assert key events only (auth checks, final status) - not every event in sequence

## Implementation Steps

### Step 1: Move FakeGtKitOps to erk-shared

Move from `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py` to `packages/erk-shared/src/erk_shared/integrations/gt/fake_kit.py`:

- Move `GitHubBuilderState` dataclass
- Move `FakeGtKitOps` class
- Update dot-agent-kit tests to import from new location

### Step 2: Create Test Infrastructure

Create test directory: `packages/erk-shared/tests/unit/integrations/gt/operations/`

Files:

- `__init__.py`
- `conftest.py` - with `collect_events` helper:

```python
def collect_events[T](generator: Generator[ProgressEvent | CompletionEvent[T]]) -> tuple[list[ProgressEvent], T]:
    """Collect progress events and final result from operation generator."""
    progress_events = []
    for event in generator:
        if isinstance(event, ProgressEvent):
            progress_events.append(event)
        elif isinstance(event, CompletionEvent):
            return progress_events, event.result
    raise RuntimeError("No completion event")
```

### Step 3: Write Tests for Each Operation

#### test_prep.py (execute_prep)

Test scenarios:

- **Success path**: Auth OK, branch exists, parent exists, no conflicts, squash (or skip), diff extracted
  - Assert key events: "Authenticated as...", "No restack conflicts", "Diff retrieved"
- **gt_not_authenticated**: Assert error before any git operations
- **gh_not_authenticated**: Assert gt auth passed, gh auth failed
- **no_branch**: Assert auth passed, then no_branch error
- **no_parent**: Assert branch found, then no_parent error
- **restack_conflict**: Assert conflict error with details
- **no_commits**: Assert no_commits error
- **squash_conflict**: Assert squash conflict error
- **squash_failed**: Assert generic squash failure

#### test_squash.py (execute_squash)

Test scenarios:

- **no_commits**: Error when no commits ahead of trunk
- **single_commit**: Success with "already_single_commit" action
- **multiple_commits**: Success with "squashed" action
- **squash_conflict**: Conflict during squash
- **squash_failed**: Generic failure

#### test_update_pr.py (execute_update_pr)

Test scenarios:

- **success_with_uncommitted**: Stage, commit, restack, submit, return PR info
- **success_without_uncommitted**: Skip staging, proceed
- **add_failure**: Stage fails
- **commit_failure**: Commit fails
- **restack_conflict**: Conflict during restack
- **restack_failure**: Generic restack failure
- **remote_divergence**: Branch diverged from remote
- **submit_failure**: Generic submit failure

#### test_finalize.py (execute_finalize)

Test scenarios:

- **success**: PR metadata updated, cleanup done
- **validation_errors**: Neither/both pr_body and pr_body_file provided

### Step 4: Update dot-agent-kit Test Imports

Update imports in:

- `packages/dot-agent-kit/tests/unit/kits/gt/test_*.py`

From:

```python
from tests.unit.kits.gt.fake_ops import FakeGtKitOps
```

To:

```python
from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
```

## Files to Create

1. `packages/erk-shared/src/erk_shared/integrations/gt/fake_kit.py`
2. `packages/erk-shared/tests/unit/integrations/__init__.py`
3. `packages/erk-shared/tests/unit/integrations/gt/__init__.py`
4. `packages/erk-shared/tests/unit/integrations/gt/operations/__init__.py`
5. `packages/erk-shared/tests/unit/integrations/gt/operations/conftest.py`
6. `packages/erk-shared/tests/unit/integrations/gt/operations/test_prep.py`
7. `packages/erk-shared/tests/unit/integrations/gt/operations/test_squash.py`
8. `packages/erk-shared/tests/unit/integrations/gt/operations/test_update_pr.py`
9. `packages/erk-shared/tests/unit/integrations/gt/operations/test_finalize.py`

## Files to Modify

1. `packages/dot-agent-kit/tests/unit/kits/gt/test_idempotent_squash.py` - update import
2. `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_update.py` - update import
3. `packages/dot-agent-kit/tests/unit/kits/gt/test_land_pr.py` - update import
4. `packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py` - update import
5. `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_prep.py` - update import
6. Delete `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py` after migration

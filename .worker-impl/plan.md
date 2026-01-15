# Plan: Use PlanHeaderFieldName Constants Across Codebase

## Summary

Refactor all hardcoded plan-header field name strings to use the module-level constants from `schemas.py`, ensuring type-safe access to plan-header data throughout the codebase.

## Files to Modify

### 1. `plan_header.py` (29 locations)
**Path:** `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py`

**Import to add:**
```python
from erk_shared.github.metadata.schemas import (
    CREATED_AT,
    CREATED_BY,
    CREATED_FROM_SESSION,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_NODE_ID,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_AT,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_LOCAL_IMPL_SESSION,
    LAST_LOCAL_IMPL_USER,
    LAST_REMOTE_IMPL_AT,
    OBJECTIVE_ISSUE,
    PLAN_COMMENT_ID,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
)
```

**Locations to update:**

| Line | Current | Change to |
|------|---------|-----------|
| 76 | `"schema_version": "2"` | `SCHEMA_VERSION: "2"` |
| 77 | `"created_at": created_at` | `CREATED_AT: created_at` |
| 78 | `"created_by": created_by` | `CREATED_BY: created_by` |
| 79 | `"plan_comment_id": ...` | `PLAN_COMMENT_ID: ...` |
| 80-88 | All field assignments | Use constants |
| 91 | `data["worktree_name"]` | `data[WORKTREE_NAME]` |
| 95 | `data["source_repo"]` | `data[SOURCE_REPO]` |
| 99 | `data["objective_issue"]` | `data[OBJECTIVE_ISSUE]` |
| 103 | `data["created_from_session"]` | `data[CREATED_FROM_SESSION]` |
| 107 | `data["last_learn_session"]` | `data[LAST_LEARN_SESSION]` |
| 111 | `data["last_learn_at"]` | `data[LAST_LEARN_AT]` |
| 273-275 | Dispatch field updates | Use constants |
| 305-307 | `.get()` calls for dispatch | Use constants |
| 325 | `.get("worktree_name")` | `.get(WORKTREE_NAME)` |
| 341 | `.get("plan_comment_id")` | `.get(PLAN_COMMENT_ID)` |
| 371 | `["plan_comment_id"]` | `[PLAN_COMMENT_ID]` |
| 412 | `["last_local_impl_at"]` | `[LAST_LOCAL_IMPL_AT]` |
| 453 | `["worktree_name"]` | `[WORKTREE_NAME]` |
| 480 | `.get("last_local_impl_at")` | `.get(LAST_LOCAL_IMPL_AT)` |
| 514-517 | Local impl field updates | Use constants |
| 544 | `.get("last_local_impl_event")` | `.get(LAST_LOCAL_IMPL_EVENT)` |
| 574 | `["last_remote_impl_at"]` | `[LAST_REMOTE_IMPL_AT]` |
| 601 | `.get("last_remote_impl_at")` | `.get(LAST_REMOTE_IMPL_AT)` |
| 617 | `.get("source_repo")` | `.get(SOURCE_REPO)` |
| 633 | `.get("objective_issue")` | `.get(OBJECTIVE_ISSUE)` |
| 649 | `.get("created_from_session")` | `.get(CREATED_FROM_SESSION)` |
| 665 | `.get("last_local_impl_session")` | `.get(LAST_LOCAL_IMPL_SESSION)` |
| 698-699 | Learn field updates | Use constants |
| 726 | `.get("last_learn_session")` | `.get(LAST_LEARN_SESSION)` |
| 742 | `.get("last_learn_at")` | `.get(LAST_LEARN_AT)` |

### 2. `impl_folder.py` (2 locations)
**Path:** `packages/erk-shared/src/erk_shared/impl_folder.py`

**Import to add:**
```python
from erk_shared.github.metadata.schemas import CREATED_BY, LAST_DISPATCHED_RUN_ID
```

**Locations:**
- Line 313: `block.data.get("created_by")` → `block.data.get(CREATED_BY)`
- Line 346: `block.data.get("last_dispatched_run_id")` → `block.data.get(LAST_DISPATCHED_RUN_ID)`

### 3. `plan_store/github.py` (3 locations)
**Path:** `packages/erk-shared/src/erk_shared/plan_store/github.py`

**Import to add:**
```python
from erk_shared.github.metadata.schemas import (
    CREATED_FROM_SESSION,
    OBJECTIVE_ISSUE,
    SOURCE_REPO,
)
```

**Locations:**
- Line 258: `metadata.get("source_repo")` → `metadata.get(SOURCE_REPO)`
- Line 262: `metadata.get("objective_issue")` → `metadata.get(OBJECTIVE_ISSUE)`
- Line 272: `metadata.get("created_from_session")` → `metadata.get(CREATED_FROM_SESSION)`

## Implementation Order

1. **plan_header.py** - Largest file, most changes
2. **impl_folder.py** - Small, quick changes
3. **plan_store/github.py** - Small, quick changes

## Verification

```bash
# Type check all modified files
make ty

# Run tests for plan-header functionality
uv run pytest tests/shared/github/test_plan_header.py -v

# Run tests for impl_folder
uv run pytest tests/shared/test_impl_folder.py -v

# Run tests for plan_store
uv run pytest tests/shared/plan_store/ -v
```

## Benefits

- **Type safety**: Typos in field names caught at development time
- **IDE autocomplete**: Better developer experience
- **Single source of truth**: Field names defined in one place
- **Refactoring safety**: Changes to field names tracked across codebase
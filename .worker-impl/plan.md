---
steps:
  - name: "Fix get_pr_review_comments.py - add assert for type narrowing"
  - name: "Fix claude_settings.py - change dict to Mapping[str, Any]"
  - name: "Fix init.py - remove ignores after claude_settings.py fix"
  - name: "Fix operations.py - add casts for dict access"
  - name: "Fix list_cmd.py - add cast to ArtifactType"
  - name: "Fix decorators.py - cast wrapper return"
  - name: "Run type checker and verify all fixes pass"
  - name: "Update objective #3816 with accurate inventory"
---

# Plan: Phase 1B Type Ignore Fixes (Revised Scope)

**Part of Objective #3816, Phase 1B: Cast-Based Fixes**

## Context

The original Phase 1B scope in the objective is outdated. Files like `help_formatter.py` and `context.py` were already fixed in PR #3868 (Phase 1A steelthread). This plan addresses the **actual remaining ignores** that fit the "cast-based trivial fix" pattern.

## Current Inventory: 32 type ignores in production code

| File | Count | Category |
|------|-------|----------|
| `get_pr_discussion_comments.py` | 7 | Sentinel narrowing after isinstance+exit |
| `preflight.py` | 5 | Sentinel narrowing, tuple unpacking |
| `impl_folder.py` | 4 | File-level + dict access |
| `claude_settings.py` | 3 | Function parameter type annotation |
| `operations.py` | 3 | Dict.get() typing |
| `sync_cmd.py` | 2 | SquashResult narrowing |
| `init.py` | 2 | Calls to claude_settings functions |
| `get_pr_review_comments.py` | 2 | Return type after NoReturn |
| `tui/app.py` | 2 | Conditional import |
| `decorators.py` | 1 | Wrapper return type |
| `list_cmd.py` | 1 | Literal assignment |
| `submit_cmd.py` | 1 | File-level ignore |
| `reply_to_discussion_comment.py` | 1 | File-level ignore |
| `github/real.py` | 1 | Return type |

## Revised Phase 1B Scope: 12 fixes across 6 files

Focus on **trivial cast-based fixes** using established patterns.

### In Scope

| File | Ignores | Fix Pattern |
|------|---------|-------------|
| `claude_settings.py` | 3 | TypedDict for settings parameter |
| `init.py` | 2 | Cast when passing settings |
| `operations.py` | 3 | Cast dict access, assert narrowing |
| `list_cmd.py` | 1 | Cast to Literal type (match `show.py` pattern) |
| `decorators.py` | 1 | Cast wrapper return |
| `get_pr_review_comments.py` | 2 | Mark `exit_with_error` as NoReturn |

### Deferred

- **Phase 1C:** `get_pr_discussion_comments.py`, `preflight.py`, `sync_cmd.py` (need helper functions)
- **Phase 1D:** `tui/app.py`, `github/real.py` (misc)
- **Phase 1E:** `submit_cmd.py`, `reply_to_discussion_comment.py`, `impl_folder.py` (file-level)

---

## Implementation Plan

### Step 1: Fix get_pr_review_comments.py (2 ignores)

**Root cause:** Type checker (`ty`) doesn't narrow after `NoReturn` path. Even though `exit_with_error()` is correctly typed as `NoReturn`, `ty` doesn't infer that `branch` is non-None after the early exit.

**Pattern:** Add explicit assertion for type narrowing:

```python
def _ensure_branch(branch: str | None) -> str:
    if branch is None:
        exit_with_error("branch_detection_failed", "Could not determine current branch")
    assert branch is not None  # Type narrowing after NoReturn
    return branch

def _ensure_pr_result(...) -> PRDetails:
    if isinstance(pr_result, PRNotFound):
        if branch is not None:
            exit_with_error("no_pr_for_branch", f"No PR found for branch '{branch}'")
        else:
            exit_with_error("pr_not_found", f"PR #{pr_number} not found")
    assert not isinstance(pr_result, PRNotFound)  # Type narrowing
    return pr_result
```

**Files:** `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py`

### Step 2: Fix claude_settings.py (3 ignores)

**Root cause:** Functions accept `dict` but type checker wants specific types.

**Pattern:** Use `Mapping[str, Any]` which accepts any dict-like type.

```python
from collections.abc import Mapping
from typing import Any

def has_user_prompt_hook(settings: Mapping[str, Any]) -> bool:
def has_exit_plan_hook(settings: Mapping[str, Any]) -> bool:
def add_erk_hooks(settings: Mapping[str, Any]) -> dict[str, Any]:
```

**Files:** `src/erk/core/claude_settings.py`

### Step 3: Fix init.py (2 ignores)

After Step 2, calls at lines 327, 338 should typecheck since `dict` is a `Mapping`.

If still failing, add explicit cast:
```python
from typing import cast, Any
from collections.abc import Mapping

cast(Mapping[str, Any], settings)
```

**Files:** `src/erk/cli/commands/init.py`

### Step 4: Fix operations.py (3 ignores)

**Lines 130-131:** `item.get("action")` and `item.get("warning")`

After `isinstance(item, dict)` check at line 126, cast the item:
```python
if not isinstance(item, dict):
    errors.append(f"Field 'tripwires[{i}]' must be an object")
    continue

# After dict check, item is dict but needs cast for proper get() typing
item_dict = cast(dict[str, Any], item)
action = item_dict.get("action")
warning = item_dict.get("warning")
```

**Line 199:** `read_when=read_when` after assertions at 195-196

Add assert for list[str]:
```python
assert isinstance(title, str)
assert isinstance(read_when, list) and all(isinstance(x, str) for x in read_when)
# Or simpler: cast
read_when_typed = cast(list[str], read_when)
```

**Files:** `src/erk/agent_docs/operations.py`

### Step 5: Fix list_cmd.py (1 ignore)

**Line 47:** `typed_filter: ArtifactType = artifact_type`

**Pattern:** Match existing `show.py` pattern at line 46:
```python
from typing import cast
typed_filter = cast(ArtifactType, artifact_type)
```

**Files:** `src/erk/cli/commands/artifact/list_cmd.py`

### Step 6: Fix decorators.py (1 ignore)

**Line 278:** `return wrapper`

**Pattern:** Cast to expected return type:
```python
from typing import cast, Callable, Any
return cast(Callable[..., Any], wrapper)
```

Or adjust type signature of the decorator itself.

**Files:** `src/erk/hooks/decorators.py`

### Step 7: Run type checker and verify

Run `uv run ty check src/ packages/` to verify all fixes pass.

---

## Files to Modify

1. `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py` - Add assert for type narrowing
2. `src/erk/core/claude_settings.py` - Change `dict` to `Mapping[str, Any]`
3. `src/erk/cli/commands/init.py` - Remove ignores (should work after step 2)
4. `src/erk/agent_docs/operations.py` - Add casts for dict access
5. `src/erk/cli/commands/artifact/list_cmd.py` - Add cast (match show.py)
6. `src/erk/hooks/decorators.py` - Cast wrapper return

## Test Requirements

- Run type checker (`uv run ty check src/ packages/`)
- Run existing unit tests to verify no regressions
- No new tests needed (behavioral changes are minimal)

---

## Post-Implementation: Update Objective Issue

After PR lands, update objective #3816:

1. Mark Phase 1B steps as done with PR link
2. Update "Exploration Notes" with accurate remaining inventory
3. Update "Current Focus" to next phase

The objective's Phase 1B originally listed files that were already fixed in Phase 1A. The updated inventory should reflect what actually remains.

## Related Documentation

- **Skills:** `dignified-python` (cast vs ignore guidance)
- **Reference:** `src/erk/cli/commands/artifact/show.py:46` (existing cast pattern)
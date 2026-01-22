# Plan: Consolidate Parent-is-Trunk Validation (Objective #5466, Phase 1)

## Goal

Create a shared validation helper for parent-is-trunk validation and update both CLI and gateway layers to use it. This eliminates duplicate validation logic while preserving the defense-in-depth architecture.

## Context

**Current state:** Two identical validation checks exist:
- **CLI layer:** `land_cmd.py:1200-1206` uses `Ensure.invariant()`
- **Gateway layer:** `land_pr.py:54-74` yields `LandPrError`

Both have identical error messages but different error handling mechanisms.

**Design decision from objective:** Keep defense-in-depth (both layers validate), but share the validation code.

## Implementation

### Step 1: Create shared validation module

**File:** `packages/erk-shared/src/erk_shared/stack/__init__.py` (empty, for package)
**File:** `packages/erk-shared/src/erk_shared/stack/validation.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ParentNotTrunkError:
    """Validation error when branch parent is not trunk."""
    current_branch: str
    parent_branch: str | None
    trunk_branch: str

    @property
    def message(self) -> str:
        return (
            f"Branch must be exactly one level up from {self.trunk_branch}\n"
            f"Current branch: {self.current_branch}\n"
            f"Parent branch: {self.parent_branch or 'unknown'} (expected: {self.trunk_branch})\n\n"
            f"Please navigate to a branch that branches directly from {self.trunk_branch}."
        )

def validate_parent_is_trunk(
    *,
    current_branch: str,
    parent_branch: str | None,
    trunk_branch: str,
) -> ParentNotTrunkError | None:
    """Validate that a branch's parent is trunk.

    Returns None if valid, ParentNotTrunkError if invalid.
    """
    if parent_branch != trunk_branch:
        return ParentNotTrunkError(
            current_branch=current_branch,
            parent_branch=parent_branch,
            trunk_branch=trunk_branch,
        )
    return None
```

**Rationale:**
- Frozen dataclass stores structured error data
- `message` property generates the user-facing message
- Returns error object or None (no exception raising)
- CLI extracts `.message` for `Ensure.invariant()`
- Gateway converts to `LandPrError` with `error_type="parent-not-trunk"`

### Step 2: Update CLI layer (`_land_current_branch()`)

**File:** `src/erk/cli/commands/land_cmd.py`
**Lines:** 1196-1206

```python
# Before:
if ctx.branch_manager.is_graphite_managed():
    parent = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    trunk = ctx.git.detect_trunk_branch(repo.root)
    Ensure.invariant(
        parent == trunk,
        f"Branch must be exactly one level up from {trunk}\n"
        f"Current branch: {current_branch}\n"
        f"Parent branch: {parent or 'unknown'} (expected: {trunk})\n\n"
        f"Please navigate to a branch that branches directly from {trunk}.",
    )

# After:
if ctx.branch_manager.is_graphite_managed():
    parent = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    trunk = ctx.git.detect_trunk_branch(repo.root)
    validation_error = validate_parent_is_trunk(
        current_branch=current_branch,
        parent_branch=parent,
        trunk_branch=trunk,
    )
    Ensure.invariant(validation_error is None, validation_error.message if validation_error else "")
```

**Add import:**
```python
from erk_shared.stack.validation import validate_parent_is_trunk
```

### Step 3: Update gateway layer (`execute_land_pr()`)

**File:** `packages/erk-shared/src/erk_shared/gateway/gt/operations/land_pr.py`
**Lines:** 54-74

```python
# Before:
yield ProgressEvent("Validating parent is trunk branch...")
trunk = ops.git.detect_trunk_branch(repo_root)
if parent != trunk:
    yield CompletionEvent(
        LandPrError(
            success=False,
            error_type="parent-not-trunk",
            message=(
                f"Branch must be exactly one level up from {trunk}\n"
                ...
            ),
            details={...},
        )
    )
    return

# After:
yield ProgressEvent("Validating parent is trunk branch...")
trunk = ops.git.detect_trunk_branch(repo_root)
validation_error = validate_parent_is_trunk(
    current_branch=branch_name,
    parent_branch=parent,
    trunk_branch=trunk,
)
if validation_error is not None:
    yield CompletionEvent(
        LandPrError(
            success=False,
            error_type="parent-not-trunk",
            message=validation_error.message,
            details={
                "current_branch": validation_error.current_branch,
                "parent_branch": validation_error.parent_branch or "unknown",
            },
        )
    )
    return
```

**Add import:**
```python
from erk_shared.stack.validation import validate_parent_is_trunk
```

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/stack/__init__.py` | Create (empty package) |
| `packages/erk-shared/src/erk_shared/stack/validation.py` | Create validation module |
| `src/erk/cli/commands/land_cmd.py` | Update `_land_current_branch()` |
| `packages/erk-shared/src/erk_shared/gateway/gt/operations/land_pr.py` | Update `execute_land_pr()` |
| `tests/unit/stack/__init__.py` | Create (empty package) |
| `tests/unit/stack/test_validation.py` | Create unit tests |

## Testing

### Unit tests for shared validation

```python
# tests/unit/stack/test_validation.py
def test_validate_parent_is_trunk_valid() -> None:
    result = validate_parent_is_trunk(
        current_branch="feature-1",
        parent_branch="main",
        trunk_branch="main",
    )
    assert result is None

def test_validate_parent_is_trunk_invalid() -> None:
    result = validate_parent_is_trunk(
        current_branch="feature-1",
        parent_branch="develop",
        trunk_branch="main",
    )
    assert result is not None
    assert "Branch must be exactly one level up from main" in result.message
    assert "Parent branch: develop" in result.message

def test_validate_parent_is_trunk_none_parent() -> None:
    result = validate_parent_is_trunk(
        current_branch="feature-1",
        parent_branch=None,
        trunk_branch="main",
    )
    assert result is not None
    assert "Parent branch: unknown" in result.message
```

### Verification

1. Existing test passes: `pytest tests/commands/land/test_core.py::test_land_error_from_execute_land_pr`
2. New unit tests pass: `pytest tests/unit/stack/test_validation.py`
3. CI checks pass: `make fast-ci`

## Skills to Load

- `dignified-python`: For frozen dataclass pattern, keyword-only args
- `fake-driven-testing`: For test organization

## Out of Scope

- Other validations in `_land_specific_pr()` and `_land_by_branch()` (those validate PR base ref vs trunk, which is a different check)
- Changes to error message content (preserve existing messages exactly)
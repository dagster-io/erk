# Plan: Phase 5 - Consolidate Confirmation Prompts in erk land

**Part of Objective #5466, Phase 5 (Steps 5.1-5.5)**

## Goal

Batch all confirmation prompts upfront in the validation phase rather than scattering them through execution. This provides predictable UX where users approve all confirmations before any mutations occur.

## Current State

Five confirmation points scattered across validation and cleanup phases:

| # | Location | Prompt | Default | Phase |
|---|----------|--------|---------|-------|
| 1 | `check_unresolved_comments` (L761) | "Continue anyway?" | False | Validation |
| 2 | `_prompt_async_learn_and_continue` (L307) | 3-choice menu | 1 | Validation |
| 3 | `_cleanup_slot_with_assignment` (L532) | "Unassign slot...?" | True | Cleanup |
| 4 | `_cleanup_slot_without_assignment` (L560) | "Release slot...?" | True | Cleanup |
| 5 | `_cleanup_non_slot_worktree` (L595) | "Delete branch...?" | True | Cleanup |

## Architecture Context

The land command has two phases:
1. **Validation phase** (`_land_target` → `_validate_pr_for_landing`): Prompts user, generates script, exits
2. **Execution phase** (`_execute_land_script`): Runs with `force=True` (user approved by sourcing script)

This means cleanup confirmations are only relevant during validation—execution always proceeds.

## Design

### Key Insight

Confirmations 1-2 are already in validation phase. Confirmations 3-5 are in cleanup phase but:
- Can be **determined** in validation using `determine_cleanup_type()` (from Phase 4)
- Only matter in validation (execute phase always uses `force=True`)

### Approach

1. Create `LandConfirmations` dataclass to hold pre-gathered confirmation results
2. Extend `_validate_pr_for_landing()` to gather cleanup confirmation upfront
3. Pass confirmation result through to cleanup functions
4. Cleanup functions check pre-gathered result instead of prompting

### Data Flow

```
_land_target()
  └─> _validate_pr_for_landing()
        ├─> check_unresolved_comments() [unchanged]
        ├─> learn status check [unchanged]
        └─> _gather_cleanup_confirmation() [NEW]
              └─> determine_cleanup_type() [pure, already exists]
              └─> prompt based on CleanupType
              └─> return CleanupConfirmation
```

## Implementation

### Step 5.1: Inventory (already complete from exploration)

Confirmed 5 prompts as listed above. Prompts 1-2 already in validation. Prompts 3-5 need consolidation.

### Step 5.2: Create CleanupConfirmation dataclass

```python
@dataclass(frozen=True)
class CleanupConfirmation:
    """Pre-gathered cleanup confirmation result.

    Captures user's response to cleanup prompt during validation phase.
    """
    proceed: bool  # True = proceed with cleanup, False = preserve
```

Note: `LandConfirmations` is overkill since:
- Unresolved comments prompt already exits on decline
- Learn status prompt already exits on cancel
- Only cleanup confirmation needs to be passed through

### Step 5.3: Create _gather_cleanup_confirmation()

New function that:
1. Calls `determine_cleanup_type()` to classify scenario
2. Prompts based on `CleanupType` (same messages as current cleanup functions)
3. Returns `CleanupConfirmation`

```python
def _gather_cleanup_confirmation(
    ctx: ErkContext,
    *,
    target: LandTarget,
    repo: RepoContext,
    force: bool,
) -> CleanupConfirmation:
    """Gather cleanup confirmation upfront during validation."""
```

### Step 5.4: Move confirmation logic from cleanup to validation

In `_validate_pr_for_landing()`:
- Call `_gather_cleanup_confirmation()` at the end
- Return `CleanupConfirmation` (change return type from None)

Modify `CleanupContext`:
- Add `cleanup_confirmed: bool` field

Modify cleanup functions:
- Remove `ctx.console.confirm()` calls
- Check `cleanup.cleanup_confirmed` instead
- Keep early-return for `cleanup_confirmed=False`

### Step 5.5: Thread confirmation through execution

1. `_validate_pr_for_landing()` returns `CleanupConfirmation`
2. `_land_target()` passes to script generation (confirmation already gathered)
3. In execute phase: `force=True` means `cleanup_confirmed=True`
4. `_cleanup_and_navigate()` creates `CleanupContext` with correct `cleanup_confirmed`

## Files to Modify

- `src/erk/cli/commands/land_cmd.py` (primary, all changes here)

## Test Strategy

1. **Existing tests pass**: All current land tests should continue to pass
2. **Confirmation order**: Manual test that confirmations appear in predictable order:
   - Unresolved comments (if any)
   - Learn status (if applicable)
   - Cleanup action (if applicable)
3. **Early exit preserved**: Declining any confirmation still aborts appropriately
4. **force flag**: `--force` still skips all confirmations
5. **dry-run**: `--dry-run` still shows what would happen without prompting

## Verification

```bash
# Run existing tests
make fast-ci

# Manual test scenarios:
# 1. Land with unresolved comments (should prompt first)
# 2. Land plan branch without learning (should prompt for learn choice)
# 3. Land in slot worktree (should prompt for cleanup)
# 4. Land with --force (should skip all prompts)
# 5. Land with --dry-run (should show plan without prompts)
```

## Notes

- The learn status prompt is a 3-choice menu (not a simple confirm)—unchanged
- `check_unresolved_comments()` has API error handling—unchanged
- Script mode behavior (non-interactive) must be preserved
- Execute phase always uses `force=True`, so confirmations only matter in validation

## Detailed Changes

### New dataclass

```python
@dataclass(frozen=True)
class CleanupConfirmation:
    """Pre-gathered cleanup confirmation result."""
    proceed: bool
```

### New function

```python
def _gather_cleanup_confirmation(
    ctx: ErkContext,
    *,
    target: LandTarget,
    repo: RepoContext,
    force: bool,
) -> CleanupConfirmation:
    """Gather cleanup confirmation upfront during validation.

    Uses determine_cleanup_type() to classify the cleanup scenario,
    then prompts based on the classification. Returns result for
    threading through to cleanup functions.
    """
    if force or ctx.dry_run:
        return CleanupConfirmation(proceed=True)

    resolved = determine_cleanup_type(
        no_delete=False,  # no_delete handled separately
        worktree_path=target.worktree_path,
        pool_json_path=repo.pool_json_path,
        branch=target.branch,
    )

    match resolved.cleanup_type:
        case CleanupType.NO_DELETE | CleanupType.NO_WORKTREE:
            # No confirmation needed
            return CleanupConfirmation(proceed=True)
        case CleanupType.SLOT_ASSIGNED:
            assert resolved.assignment is not None
            proceed = ctx.console.confirm(
                f"Unassign slot '{resolved.assignment.slot_name}' "
                f"and delete branch '{target.branch}'?",
                default=True,
            )
        case CleanupType.SLOT_UNASSIGNED:
            assert target.worktree_path is not None
            user_output(
                click.style("Warning:", fg="yellow")
                + f" Slot '{target.worktree_path.name}' has no assignment..."
            )
            proceed = ctx.console.confirm(
                f"Release slot '{target.worktree_path.name}' "
                f"and delete branch '{target.branch}'?",
                default=True,
            )
        case CleanupType.NON_SLOT:
            proceed = ctx.console.confirm(
                f"Delete branch '{target.branch}'? (worktree preserved)",
                default=True,
            )
        case _:
            assert_never(resolved.cleanup_type)

    return CleanupConfirmation(proceed=proceed)
```

### Modified CleanupContext

Add `cleanup_confirmed: bool` field.

### Modified cleanup functions

Replace:
```python
if not cleanup.force and not cleanup.ctx.dry_run:
    if not cleanup.ctx.console.confirm(...):
        ...
```

With:
```python
if not cleanup.cleanup_confirmed:
    user_output("...")
    return
```
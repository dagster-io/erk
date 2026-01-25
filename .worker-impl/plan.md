# Plan: Fix Duplicate Plan Creation Loop

## Problem

11 duplicate plans (#5957-#5970) were created in 10 minutes, all with title "Prevent learn plan cycles and preserve erk-learn labels".

## Root Cause

**Key finding**: 10 of 11 plans were created by the **SAME session** (8cabe92a-9447-4089-a320-ee9130ac27e2). One session called `/erk:plan-save` 10 times.

**The bug is in `exit_plan_mode_hook.py` (line 426-432)**:

```python
if hook_input.plan_saved_marker_exists:
    return HookOutput(
        ExitAction.BLOCK,
        "✅ Plan already saved to GitHub. Session complete...",
        delete_plan_saved_marker=True,  # <-- BUG: Deletes the marker!
    )
```

**The Loop Sequence**:
1. Agent calls `/erk:plan-save` → creates plan-saved marker → issue #1 created
2. Agent calls ExitPlanMode
3. Hook sees marker, blocks with "session complete", **deletes marker**
4. Agent calls ExitPlanMode again (ignoring the block message)
5. Hook sees NO marker, plan still exists → prompts user again
6. Agent chooses "Save the plan" → runs `/erk:plan-save` again → issue #2 created
7. Loop repeats (10 times in this case)

## Fix

### Primary Fix: Don't Delete plan-saved Marker on Block

**File**: `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

Change line 431 from:
```python
delete_plan_saved_marker=True,
```
to:
```python
delete_plan_saved_marker=False,
```

This keeps the marker in place, so subsequent ExitPlanMode calls still block with "session complete".

### Secondary Safeguard: Add Session-Based Deduplication to plan-save-to-issue

**File**: `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

Before creating a new issue, check if this session already saved a plan:

```python
# Check if this session already saved a plan
marker_path = get_scratch_dir(session_id, repo_root) / "plan-saved-issue.marker"
if marker_path.exists():
    existing_issue = marker_path.read_text(encoding="utf-8").strip()
    user_output(f"This session already saved plan #{existing_issue}. Skipping duplicate creation.")
    # Return the existing issue info instead of creating a new one
    return existing_issue
```

## Files to Modify

1. `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` - Don't delete marker on block (line 431)
2. `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` - Add session deduplication check

## Cleanup (Manual)

Close the duplicate plans, keeping #5957 (the first one):

```bash
for i in 5959 5960 5961 5962 5964 5966 5967 5968 5969 5970; do
  gh issue close $i --comment "Duplicate created by exit-plan-mode-hook bug - see #5957"
done
```

## Verification

1. After fix, run `/erk:plan-save` in a session
2. Try to exit plan mode - should block with "session complete"
3. Try to exit again - should still block (not prompt to save again)
4. Manually call `/erk:plan-save` again - should skip and return existing issue number

## Test Changes

Update existing tests in `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`:

1. `test_plan_saved_marker_blocks_and_deletes` (line 136):
   - Change: `assert result.delete_plan_saved_marker is True` → `is False`
   - Rename to: `test_plan_saved_marker_blocks_and_preserves`

2. `test_plan_saved_deletes_objective_context_marker_when_present` (line 180):
   - Change: `assert result.delete_plan_saved_marker is True` → `is False`
   - Note: `delete_objective_context_marker` should stay True (different marker)
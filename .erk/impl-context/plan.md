# Plan: Align `erk pr teleport` default behavior with `erk br co`

## Context

`erk pr teleport`'s in-place path lacks the slot awareness that `erk br co` has. When in a slot-assigned worktree, `erk br co` does stack-in-place (updates the slot assignment). Teleport ignores slots entirely.

Goal: match `erk br co`'s checkout/navigation behavior while preserving teleport's force-reset-to-remote semantics. Maximize code reuse, remove duplication.

## Duplication to eliminate

Both `_teleport_in_place` and `_teleport_new_slot` have **near-identical** "branch already in worktree → navigate" blocks (lines 132-166 vs 219-252). Extract to a shared helper.

## Changes

### File: `src/erk/cli/commands/pr/teleport_cmd.py`

#### 1. Extract `_navigate_to_existing_worktree` helper

Extract the duplicated pattern from both functions into:

```python
def _navigate_to_existing_worktree(
    ctx: ErkContext,
    *,
    repo_root: Path,
    pr_number: int,
    branch_name: str,
    script: bool,
) -> None:
    """Check if branch is already in a worktree; if so, navigate and exit."""
    existing = ctx.git.worktree.find_worktree_for_branch(repo_root, branch_name)
    if existing is None:
        return  # Not found, caller continues
    # Navigate, print activation, exit(0) — shared between both paths
    ...
    raise SystemExit(0)
```

Both `_teleport_in_place` and `_teleport_new_slot` call this at the top, replacing their duplicated blocks.

#### 2. Add slot awareness to `_teleport_in_place`

After force-resetting the branch (line 181), before Graphite registration:

```python
# Slot awareness: update assignment if in a managed slot (matches erk br co)
state = load_pool_state(repo.pool_json_path)
if state is not None:
    current_assignment = find_assignment_by_worktree(state, ctx.git, cwd)
    if current_assignment is not None:
        update_slot_assignment_tip(
            repo.pool_json_path, state, current_assignment,
            branch_name=branch_name, now=ctx.time.now().isoformat(),
        )
```

**New imports:**
- `from erk.core.worktree_pool import load_pool_state`
- `from erk.cli.commands.slot.common import update_slot_assignment_tip, find_assignment_by_worktree`

### File: `tests/commands/pr/test_teleport.py`

Add test: `test_teleport_in_place_updates_slot_assignment` — teleport in a slot-assigned worktree should update the slot assignment to the new branch.

## Files to modify

- `src/erk/cli/commands/pr/teleport_cmd.py` — extract helper, add slot awareness
- `tests/commands/pr/test_teleport.py` — add slot-awareness test

## Verification

1. `uv run pytest tests/commands/pr/test_teleport.py`
2. `uv run ruff check src/erk/cli/commands/pr/teleport_cmd.py`
3. `uv run ty check src/erk/cli/commands/pr/teleport_cmd.py`

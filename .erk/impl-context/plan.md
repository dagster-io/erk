# Plan: Refactor teleport dry-run from boolean threading to action plan pattern

## Context

The `--dry-run` flag on `erk pr teleport` currently threads a `dry_run: bool` parameter through 3 functions (`pr_teleport` → `_teleport_in_place` / `_teleport_new_slot`). Each inner function has an `if dry_run:` block that gathers state, calls `_display_dry_run_report()`, and exits. This boolean threading is a code smell — a `TeleportPlan` dataclass can capture what would happen, letting the top-level function decide to display or execute. This follows the existing `ConsolidationPlan` pattern in `src/erk/core/consolidation_utils.py`.

## File to Modify

- `src/erk/cli/commands/pr/teleport_cmd.py` — sole production file

## Implementation

### Step 1: Add `TeleportPlan` frozen dataclass

Add after imports (~line 35). Fields are a direct lift of `_display_dry_run_report`'s keyword arguments:

```python
@dataclass(frozen=True)
class TeleportPlan:
    """Describes what a teleport operation will do, without executing it."""
    pr_number: int
    branch_name: str
    base_ref_name: str
    ahead: int
    behind: int
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    is_new_slot: bool
    branch_exists_locally: bool
    is_graphite_managed: bool
    trunk: str
    sync: bool
    has_slot: bool
```

Add `from dataclasses import dataclass` import.

### Step 2: Change `_display_dry_run_report` to accept `TeleportPlan`

Change signature from 14 keyword args to `(plan: TeleportPlan) -> None`. Update body to read `plan.field` instead of bare `field`. Output strings stay identical.

### Step 3: Refactor `_teleport_in_place` → plan builder + executor

**Rename/restructure**: `_teleport_in_place` keeps pre-checks (navigate, fetch, ahead/behind, "already in sync" exit) and now builds + returns a `TeleportPlan`. Remove `dry_run` from its signature. Return type becomes `TeleportPlan`.

The state-gathering logic currently inside `if dry_run:` (file status, trunk, graphite, slot check) moves to always run, producing the plan.

**Extract** `_execute_in_place_teleport()`: contains the mutation logic currently after the `if dry_run:` block — confirmation prompt, create_branch(force=True), checkout, slot update, register graphite, navigate+display. Signature:

```python
def _execute_in_place_teleport(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    plan: TeleportPlan,
    force: bool,
    script: bool,
) -> None:
```

Takes `plan` to access `branch_exists_locally` (needed for confirm check) and `branch_name`/`base_ref_name`/`sync`/`pr_number`.

### Step 4: Refactor `_teleport_new_slot` → plan builder + executor

Same pattern. Remove `dry_run` from signature, return `TeleportPlan`.

Key difference: the current dry-run block calls `fetch_branch()` (line 334) but this is unnecessary for plan-building — the plan fields (branch_exists_locally, trunk, is_graphite_managed) don't depend on fetched state. Remove this fetch from the plan builder. It still happens during execution via `_fetch_and_update_branch()`.

**Extract** `_execute_new_slot_teleport()`: contains `_fetch_and_update_branch`, `_register_with_graphite`, `ensure_branch_has_worktree`, navigate+display, activation instructions.

### Step 5: Update `pr_teleport()` orchestration

Replace the current routing with plan-then-decide:

```python
if new_slot:
    plan = _teleport_new_slot(ctx, repo, ...)
else:
    plan = _teleport_in_place(ctx, repo, ...)

if dry_run:
    _display_dry_run_report(plan)
    raise SystemExit(0)

if new_slot:
    _execute_new_slot_teleport(ctx, repo, plan=plan, ...)
else:
    _execute_in_place_teleport(ctx, repo, plan=plan, ...)
```

`dry_run` now exists only in `pr_teleport()`. No boolean threading.

## Function Layout After Refactoring

```
TeleportPlan                         # frozen dataclass
pr_teleport()                        # CLI entry — only place dry_run is checked
_teleport_in_place() → TeleportPlan  # pre-checks + plan building
_teleport_new_slot() → TeleportPlan  # pre-checks + plan building
_execute_in_place_teleport()         # mutations for in-place flow
_execute_new_slot_teleport()         # mutations for new-slot flow
_display_dry_run_report()            # display a TeleportPlan
_navigate_to_existing_worktree()     # unchanged
_register_with_graphite()            # unchanged
_confirm_overwrite()                 # unchanged
```

## Edge Cases

- **"Already in sync" exit**: Happens inside `_teleport_in_place` before plan building via `raise SystemExit(0)`. Behavior-preserving for both dry-run and normal flow.
- **Navigate to existing worktree**: Also exits via `SystemExit(0)` before plan building. No plan returned in this case.
- **Double fetch for new-slot removed**: Current dry-run fetches then displays; normal flow fetches via `_fetch_and_update_branch`. After refactoring, plan builder doesn't fetch (unnecessary), execute does. Net: one fewer fetch in dry-run mode.
- **Plan-building side effects**: All calls are read-only (get_file_status, detect_trunk_branch, is_graphite_managed, load_pool_state). Safe in both flows.

## Verification

1. Run existing teleport tests: `pytest tests/commands/pr/test_teleport.py -q`
2. Run type checker: `ty check src/erk/cli/commands/pr/teleport_cmd.py`
3. Run linter: `ruff check src/erk/cli/commands/pr/teleport_cmd.py`
4. Manual smoke test: `erk pr teleport <PR> --dry-run` should produce identical output to current

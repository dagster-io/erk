# Plan: Objective #9272 Node 1.4 — Move Branch Checkout into Slot Checkout

## Context

Part of **Objective #9272: Extract Slot System into Plugin Package**.

Nodes 1.1-1.3 created the `erk-slots` workspace package, set up conditional loading, and moved slot CLI commands + `common.py`. Node 1.4 consolidates checkout into the slot system: `erk branch checkout` (707 lines of complex checkout logic) gets merged into `erk slot checkout` (currently 110 lines of basic slot allocation), then `erk branch checkout` is removed from core.

**Key behavioral change:** When a branch is not found in any existing worktree, the unified command allocates a slot instead of doing a plain `git checkout` in the current worktree. This makes the slot system the primary worktree management path.

## Phase 1: Rewrite `erk slot checkout` with full unified logic

**File:** `packages/erk-slots/src/erk_slots/checkout_cmd.py` (rewrite from ~110 to ~750 lines)

Move all helper functions from `src/erk/cli/commands/branch/checkout_cmd.py`:
- `try_switch_root_worktree()` (L41-77) — root worktree takeover for trunk
- `_ensure_graphite_tracking()` (L80-128) — idempotent Graphite tracking
- `_format_worktree_info()` (L131-147) — display helper
- `_perform_checkout()` (L150-260) — checkout + activation script + sync status + navigation
- `_find_containing_worktree()` (L262-285) — find worktree containing cwd
- `_find_root_worktree()` (L288-300) — root worktree lookup
- `_setup_impl_for_plan()` (L303-356) — `.erk/impl-context/` setup for `--for-plan`
- `_rebase_and_track_for_plan()` (L359-413) — rebase stacked plans + Graphite track

These are only used by checkout — no other callers in the codebase.

**New Click command signature** (merges options from both old commands):
```python
@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("branch", metavar="BRANCH", required=False, shell_complete=complete_branch_names)
@click.option("--for-plan", ...)
@click.option("--new-slot", is_flag=True, ...)
@click.option("-f", "--force", is_flag=True, ...)
@script_option
@click.pass_obj
def slot_checkout(ctx, branch, for_plan, new_slot, force, script): ...
```

**Unified decision tree** in `_slot_checkout_impl()`:
1. Validate args (BRANCH vs `--for-plan` mutual exclusivity)
2. Discover repo, ensure metadata
3. If `--for-plan`: resolve plan, derive branch, handle branch creation/tracking
4. Verify branch exists (create tracking from remote if needed)
5. Find worktrees containing the branch via `find_worktrees_containing_branch()`
6. Decision tree:
   - **Found in worktree(s)** → navigate to it (from branch checkout logic)
   - **Not found + trunk + clean root** → takeover root worktree
   - **Not found + in a slot + not `--new-slot`** → stack-in-place via `update_slot_assignment_tip()`
   - **Not found** → allocate new slot via `allocate_slot_for_branch()`
7. For each path: handle `--for-plan` setup, Graphite tracking, navigation, sync status via `_perform_checkout()`

**Imports from core erk** (established pattern — erk_slots already imports from core at runtime):
- `erk.cli.activation` — activation script rendering
- `erk.cli.commands.checkout_helpers` — `navigate_to_worktree`, `display_sync_status`, `script_error_handler`
- `erk.cli.commands.completions` — `complete_branch_names`
- `erk.cli.commands.pr.dispatch_helpers` — `sync_branch_to_sha`
- `erk.cli.github_parsing` — `parse_issue_identifier`
- `erk.cli.graphite` — `find_worktrees_containing_branch`
- `erk.cli.help_formatter` — `CommandWithHiddenOptions`, `script_option`
- `erk.core.worktree_utils` — `compute_relative_path_in_worktree`
- `erk_shared.*` — alias, impl_folder, output, plan_store types, plan_workflow, gateway types

## Phase 2: Update slot group registration for alias

**File:** `packages/erk-slots/src/erk_slots/__init__.py`

Change:
```python
slot_group.add_command(slot_checkout)
```
To:
```python
register_with_aliases(slot_group, slot_checkout)
```

This enables `erk slot co` as an alias for `erk slot checkout`.

## Phase 3: Remove `erk branch checkout` from core

**Delete:** `src/erk/cli/commands/branch/checkout_cmd.py`

**Edit:** `src/erk/cli/commands/branch/__init__.py`
- Remove `from erk.cli.commands.branch.checkout_cmd import branch_checkout`
- Remove `register_with_aliases(branch_group, branch_checkout)` (change to `branch_group.add_command(...)` for remaining commands, or just remove the checkout line)

After this, `branch_group` keeps: `branch_create`, `branch_delete`, `branch_list`.

## Phase 4: Migrate tests

### 4a. Migrate branch checkout tests → slot checkout tests

**From:** `tests/commands/branch/test_checkout_cmd.py` (~14 tests)
**Into:** `packages/erk-slots/tests/unit/test_checkout_cmd.py` (expand from 8 tests)

Key adaptations per test:
- CLI invocation: `["br", "co", ...]` or `["branch", "checkout", ...]` → `["slot", "checkout", ...]`
- **Behavioral changes**: Tests that assert "checkout in current worktree without slot allocation" must be updated to expect slot allocation (this is the intended behavioral change)
- Tests that find an existing worktree and navigate → minimal changes (just CLI path)
- `--for-plan` tests → `["slot", "checkout", "--for-plan", ...]`, now allocates a slot

Delete `tests/commands/branch/test_checkout_cmd.py` after migration.

### 4b. Update `_perform_checkout` import

**File:** `tests/commands/navigation/test_checkout_messages.py`
```python
# Old:
from erk.cli.commands.branch.checkout_cmd import _perform_checkout
# New:
from erk_slots.checkout_cmd import _perform_checkout
```

All 8 tests test `_perform_checkout` directly — function signature unchanged, only import path changes.

### 4c. Update CLI paths in graphite disabled tests

**File:** `tests/commands/navigation/test_checkout_graphite_disabled.py`

Change `["branch", "checkout", ...]` / `["br", "co", ...]` → `["slot", "checkout", ...]` / `["slot", "co", ...]` in all 5 tests.

## Critical files

| File | Action |
|------|--------|
| `packages/erk-slots/src/erk_slots/checkout_cmd.py` | Rewrite (primary deliverable) |
| `packages/erk-slots/src/erk_slots/__init__.py` | Edit (alias registration) |
| `src/erk/cli/commands/branch/checkout_cmd.py` | Delete |
| `src/erk/cli/commands/branch/__init__.py` | Edit (remove checkout) |
| `packages/erk-slots/tests/unit/test_checkout_cmd.py` | Expand with migrated tests |
| `tests/commands/branch/test_checkout_cmd.py` | Delete after migration |
| `tests/commands/navigation/test_checkout_messages.py` | Edit (import path) |
| `tests/commands/navigation/test_checkout_graphite_disabled.py` | Edit (CLI paths) |

Unchanged reference files:
- `src/erk/cli/commands/checkout_helpers.py` — shared utilities stay in core (used by pr checkout, teleport, land, navigation)
- `packages/erk-slots/src/erk_slots/common.py` — slot allocation functions (reused)

## Verification

1. `uv run pytest packages/erk-slots/tests/unit/test_checkout_cmd.py` — unified checkout tests
2. `uv run pytest tests/commands/navigation/test_checkout_messages.py` — message generation
3. `uv run pytest tests/commands/navigation/test_checkout_graphite_disabled.py` — graphite degradation
4. `uv run pytest tests/commands/branch/` — remaining branch tests (create, delete, list)
5. `uv run pytest packages/erk-slots/tests/` — all slot tests
6. `uv run pytest tests/commands/` — all command tests
7. `uv run ruff check` + `uv run ty check` — lint and type check

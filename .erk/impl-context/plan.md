# Plan: Merge `erk wt create-from` into `erk wt create --from-branch`

## Context

`erk wt create-from <branch>` is a separate command that allocates a worktree **pool slot** for an existing branch. Meanwhile, `erk wt create --from-branch <branch>` does something similar but **without slot allocation** — it just creates a plain worktree via `git worktree add`.

The user wants to eliminate `create-from` as a separate command and fold its slot-allocation behavior into `erk wt create --from-branch`. This simplifies the CLI surface.

## Key Differences Today

| Feature | `create --from-branch` | `create-from` |
|---|---|---|
| Slot allocation | No | Yes (`allocate_slot_for_branch`) |
| Auto-fetch remote branches | No | Yes |
| `--force` (evict oldest slot) | No | Yes |
| Pool-full handling | No | Yes |
| Worktree naming | `sanitize_worktree_name` | Slot name (e.g. `erk-slot-01`) |
| Post-create setup (.env, commands) | Yes | No (just activation script) |

## Plan

### Step 1: Modify `--from-branch` handling in `create_cmd.py`

Replace the current `--from-branch` code path (lines ~598-606, ~814-834) to use `allocate_slot_for_branch()` instead of `add_worktree()`:

- Import `allocate_slot_for_branch` from `erk_slots.common`
- Import `navigate_to_worktree` from `erk.cli.commands.checkout_helpers`
- When `from_branch` is set:
  1. Validate branch is not trunk (already done)
  2. Auto-fetch remote branches if not local (copy logic from `create_from_cmd.py`)
  3. Call `allocate_slot_for_branch()` with `force=force` flag
  4. Navigate to the allocated slot worktree
  5. Display sync status and activation instructions
- The `--force` flag needs to be added to the `create` command (only relevant when `--from-branch` is used)

### Step 2: Add `--force` flag to `create` command

Add `--force / -f` option to `create_wt`. It should only be meaningful with `--from-branch`. Validate that `--force` is not used without `--from-branch`.

### Step 3: Handle naming and output differences

When `--from-branch` is used:
- The worktree name comes from the slot allocation (e.g., `erk-slot-01`), not from `sanitize_worktree_name`
- The `name` positional argument should be ignored/disallowed with `--from-branch` (or just not used)
- Output should match the `create-from` output (assigned/already-assigned messages)
- Return early after slot allocation — skip the normal `create` post-processing (since the slot worktree already exists)

### Step 4: Remove `create-from` command

- **Delete** `src/erk/cli/commands/wt/create_from_cmd.py`
- **Remove** registration from `src/erk/cli/commands/wt/__init__.py` (line 8 import + line 26 `add_command`)

### Step 5: Migrate tests

- **Delete** `tests/unit/cli/commands/wt/test_create_from_cmd.py`
- **Create** new tests or add to existing test file for `erk wt create --from-branch` covering:
  - Happy path: local branch exists, allocates slot
  - Remote branch auto-fetch
  - Branch not found error
  - Trunk branch error
  - Already assigned
  - Force eviction when pool full
  - Pool full without force
- Tests should invoke `["wt", "create", "--from-branch", "feature-auth"]` instead of `["wt", "create-from", "feature-auth"]`

### Step 6: Update documentation

- **Delete** `docs/learned/cli/wt-create-from.md`
- **Update** `docs/learned/cli/wt-command-comparison.md` — replace `create-from` rows with `create --from-branch`
- **Update** `docs/learned/cli/index.md` — remove `wt-create-from.md` entry
- **Update** `docs/learned/erk/same-worktree-navigation.md` — update reference to `create_from_cmd.py`

## Critical Files

- `src/erk/cli/commands/wt/create_cmd.py` — main modification target
- `src/erk/cli/commands/wt/create_from_cmd.py` — to be deleted
- `src/erk/cli/commands/wt/__init__.py` — remove registration
- `tests/unit/cli/commands/wt/test_create_from_cmd.py` — to be migrated/deleted
- `packages/erk-slots/src/erk_slots/common.py` — `allocate_slot_for_branch()` (no changes needed)

## Verification

1. Run tests for the wt create command: `uv run pytest tests/unit/cli/commands/wt/ tests/commands/`
2. Run `uv run ruff check src/erk/cli/commands/wt/`
3. Run `uv run ty check src/erk/cli/commands/wt/`
4. Manually verify `erk wt create --from-branch <branch>` allocates a slot
5. Verify `erk wt create-from` no longer exists as a command

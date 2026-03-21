# Plan: Delete branch create command (Objective #9272, Node 1.5)

## Context

Part of Objective #9272 (Extract Slot System into Plugin Package), Node 1.5.

The `erk branch create` command currently creates a branch, allocates a pool slot, and optionally sets up impl-context for `--for-pr`. After extracting slot logic to `erk_slots`, the remaining value is thin: `gt create` handles branch creation with Graphite tracking, and `erk slot checkout` / `erk slot assign` handle worktree allocation. The `--for-pr` workflow is already handled by `erk br checkout --for-pr` (which the TUI uses). Rather than simplifying `branch create` to a trivial wrapper, we delete it entirely.

## Changes

### 1. Delete `src/erk/cli/commands/branch/create_cmd.py`

Remove the file entirely.

### 2. Update `src/erk/cli/commands/branch/__init__.py`

Remove the `branch_create` import and `branch_group.add_command(branch_create)` registration.

### 3. Delete `tests/unit/cli/commands/branch/test_create_cmd.py`

Remove the test file entirely.

### 4. Update help text references (4 files)

Update error messages and docstrings that suggest `erk branch create` / `erk br create`:

| File | Current text | New text |
|------|-------------|----------|
| `src/erk/cli/commands/wt/create_from_cmd.py:62` | `erk br create {branch}` | `gt create {branch}` |
| `packages/erk-slots/src/erk_slots/checkout_cmd.py:41-42` | `Use \`erk branch create\` to create a new branch.` | `Use \`gt create\` to create a new branch.` |
| `packages/erk-slots/src/erk_slots/checkout_cmd.py:113` | `Use \`erk branch create\` to create a new branch.` | `Use \`gt create\` to create a new branch.` |
| `packages/erk-slots/src/erk_slots/assign_cmd.py:39` | `Use \`erk branch create\` to create a NEW branch and assign it.` | `Use \`gt create\` to create a NEW branch.` |
| `packages/erk-slots/src/erk_slots/assign_cmd.py:89` | `Use \`erk branch create\` to create a new branch.` | `Use \`gt create\` to create a new branch.` |

### 5. Do NOT touch (out of scope)

- `docs/learned/` references — documentation updates are separate from code changes
- Other files that reference `create_branch` as a git gateway method (not CLI command)
- `src/erk/core/slot_allocation.py` — stays for other callers until they move

## Key files

| File | Action |
|------|--------|
| `src/erk/cli/commands/branch/create_cmd.py` | Delete |
| `src/erk/cli/commands/branch/__init__.py` | Remove create registration |
| `tests/unit/cli/commands/branch/test_create_cmd.py` | Delete |
| `src/erk/cli/commands/wt/create_from_cmd.py` | Update help text |
| `packages/erk-slots/src/erk_slots/checkout_cmd.py` | Update help text |
| `packages/erk-slots/src/erk_slots/assign_cmd.py` | Update help text |

## Verification

1. Run branch command tests: `uv run pytest tests/unit/cli/commands/branch/`
2. Run slot tests (checkout, assign): `uv run pytest packages/erk-slots/tests/`
3. Run wt create-from tests: `uv run pytest tests/unit/cli/commands/wt/test_create_from_cmd.py`
4. Run type checker on modified files
5. Run fast CI: `make fast-ci`

# Complete Phase 1: .impl/ to .erk/impl-context/ consolidation

Part of Objective #8197, Nodes 1.6, 1.7, 1.8

## Context

Objective #8197 consolidates the legacy `.impl/` folder into branch-scoped `.erk/impl-context/<branch>/`. PRs #8215, #8279, and #8302 completed nodes 1.1–1.5, updating the core impl_folder module, exec scripts, and CLI commands. Three Phase 1 nodes remain before moving to test updates in Phase 2.

## Node 1.6: Update plan_data_provider to use resolve_impl_dir()

**The one critical code change.** `_build_worktree_mapping()` in the plan data provider hardcodes `worktree.path / ".impl"` instead of using `resolve_impl_dir()`.

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

- **Line 61**: Add `resolve_impl_dir` to the existing `from erk_shared.impl_folder import read_plan_ref` import
- **Lines 551-573**: In `_build_worktree_mapping()`:
  - Replace `impl_dir = worktree.path / ".impl"` (line 564) with `impl_dir = resolve_impl_dir(worktree.path, branch_name=worktree.branch)`
  - Wrap `read_plan_ref(impl_dir)` in `if impl_dir is not None:` guard (since `resolve_impl_dir` returns `Path | None`)
  - Update docstring (line 554) to reference unified discovery instead of `.impl/plan-ref.json`

## Node 1.7: Remove .impl/ from .gitignore

**File:** `.gitignore`

- Remove line 18 (`.impl/`). The `.erk/impl-context/` entry on line 21 was already added by PR #8308.

## Node 1.8: Remove impl_type tracking from \_validate_impl_folder()

The `impl_type` field distinguishes legacy `.impl/` from branch-scoped `.erk/impl-context/`. With consolidation, this distinction is meaningless.

### Files to modify:

1. **`src/erk/cli/commands/exec/scripts/impl_init.py`**
   - `_validate_impl_folder()` (line 42): Change return type from `tuple[Path, str]` to `Path`. Remove lines 75-76 (impl_type determination). Return `impl_dir` directly.
   - `impl_init()` (line 142): Change `impl_dir, impl_type = ...` to `impl_dir = ...`
   - Line 159: Remove `"impl_type": impl_type` from result dict

2. **`src/erk/cli/commands/exec/scripts/setup_impl.py`**
   - Line 62: Change `impl_dir, impl_type = ...` to `impl_dir = ...`
   - Line 74: Remove `"impl_type": impl_type` from result dict

3. **`tests/unit/cli/commands/exec/scripts/test_impl_init.py`**
   - Remove assertions checking `data["impl_type"]`

4. **`docs/learned/cli/erk-exec-commands.md`**
   - Remove `impl_type` from documented output fields

## Verification

1. Run `make fast-ci` (unit tests + lint + type check)
2. Specifically verify: `pytest tests/unit/cli/commands/exec/scripts/test_impl_init.py`
3. Specifically verify: `pytest tests/unit/status/` (impl collector tests)

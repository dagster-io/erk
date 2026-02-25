# Plan: Objective #8197 Nodes 1.1–1.3 — Branch-Scoped Impl Directory Foundation

**Objective:** [#8197 — Consolidate .impl/ into branch-scoped .erk/impl-context/<branch>/](https://github.com/dagster-io/erk/issues/8197)
**Nodes:** 1.1, 1.2, 1.3

## Context

Currently, implementation state lives in `.impl/` at the worktree root — a flat directory that can only track one plan at a time. The objective consolidates this into `.erk/impl-context/<branch>/`, enabling branch-scoped impl directories. Nodes 1.1–1.3 establish the foundation: a new path helper, updated core functions, and a standardized filename.

## Changes

### 1. `impl_folder.py` — Core changes (Nodes 1.1–1.3)

**File:** `packages/erk-shared/src/erk_shared/impl_folder.py`

**Node 1.1 — Add `IMPL_DIR_RELATIVE` constant and `get_impl_dir()` helper:**

- Add `IMPL_DIR_RELATIVE = ".erk/impl-context"` constant (after line 27)
- Add private `_sanitize_branch_for_dirname(branch_name: str) -> str` — replaces `/` with `--`
- Add `get_impl_dir(base_path: Path, branch_name: str) -> Path` — returns `base_path / IMPL_DIR_RELATIVE / sanitized_branch`. Pure path computation, no I/O.

**Node 1.2 — Update `create_impl_folder()` and `get_impl_path()`:**

- `create_impl_folder()`: Add required `branch_name: str` keyword param. Replace `worktree_path / ".impl"` with `get_impl_dir(worktree_path, branch_name)`.
- `get_impl_path()`: Add required `branch_name: str` keyword param. Replace `worktree_path / ".impl" / "plan.md"` with `get_impl_dir(worktree_path, branch_name) / "plan.md"`.

**Node 1.3 — Update `save_plan_ref()`:**

- Change output filename from `"plan-ref.json"` to `"ref.json"` (line 190)
- Update docstring references from `plan-ref.json` to `ref.json`
- Update module docstring (line 5)
- `read_plan_ref()` already handles both filenames (line 242), so reading is already compatible

### 2. Caller updates — Pass `branch_name` to compile

Every caller of `create_impl_folder()` and `get_impl_path()` must pass `branch_name`. Each site already has branch info available:

| File | Line(s) | Function Called | Branch Source |
|------|---------|----------------|---------------|
| `src/erk/cli/commands/implement.py` | 142 | `create_impl_folder` | `ctx.git.branch.get_current_branch(ctx.cwd)` — move call before line 142 (currently at line 166) |
| `src/erk/cli/commands/implement.py` | 252 | `create_impl_folder` | `ctx.git.branch.get_current_branch(ctx.cwd)` — move call before line 252 (currently at line 265) |
| `src/erk/cli/commands/implement.py` | 151 | `save_plan_ref` via hardcoded `ctx.cwd / ".impl"` | Replace with `get_impl_dir(ctx.cwd, branch)` |
| `src/erk/cli/commands/branch/create_cmd.py` | 246 | `create_impl_folder` | `branch_name` already a parameter |
| `src/erk/cli/commands/branch/checkout_cmd.py` | 296 | `create_impl_folder` | Thread `branch_name` into `_setup_impl_for_plan()` |
| `src/erk/cli/commands/wt/create_cmd.py` | 736 | `get_impl_path` | `existing_branch` at line 735 |
| `src/erk/cli/commands/wt/create_cmd.py` | 880, 898 | `create_impl_folder` | `branch` variable from worktree creation flow |
| `src/erk/cli/commands/wt/create_cmd.py` | 901 | `save_plan_ref` via `wt_path / ".impl"` | Replace with return value from `create_impl_folder` |
| `src/erk/cli/commands/wt/list_cmd.py` | 96 | `get_impl_path` | `branch` parameter at line 90 |
| `src/erk/cli/commands/exec/scripts/setup_impl.py` | 137 | `create_impl_folder` | `branch_name` at line 118 |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` | 216 | `create_impl_folder` | `branch_name` at line 165 |
| `src/erk/status/collectors/impl.py` | 35, 49 | `get_impl_path` | `ctx.git.branch.get_current_branch(worktree_path)` |
| `src/erk/status/collectors/impl.py` | 85 | hardcoded `worktree_path / ".impl"` | Replace with `get_impl_dir(worktree_path, branch)` |

### 3. Test updates

**File:** `tests/core/test_impl_folder.py`

- Add tests for `get_impl_dir()`: basic path, branch with `/`, branch without `/`
- Add test for `_sanitize_branch_for_dirname()` (import via `from erk_shared.impl_folder import _sanitize_branch_for_dirname`)
- Update all existing `create_impl_folder()` calls: add `branch_name="test-branch"`
- Update all existing `get_impl_path()` calls: add `branch_name="test-branch"`
- Update `save_plan_ref()` tests: assert output file is `ref.json`, not `plan-ref.json`
- Verify `read_plan_ref()` round-trip still works

**Other test files that call these functions:**
- `tests/core/test_impl_issue_wt_workflow.py` — add `branch_name=`
- `tests/unit/status/test_impl_collector.py` — add `branch_name=`
- `tests/unit/cli/commands/wt/test_list_helpers.py` — add `branch_name=`

## Scope boundary

This PR does **NOT** change:
- Other hardcoded `.impl` references in exec scripts beyond the direct function calls (→ node 1.4)
- Other hardcoded `.impl` references in CLI commands beyond the direct function calls (→ node 1.5)
- `IMPL_CONTEXT_DIR` in `planned_pr_lifecycle.py` (→ later consolidation)
- `.gitignore` (→ node 1.7)
- Migration of existing `.impl/` directories (→ node 1.9)
- `impl_context.py` (the staging directory module) — remains unchanged

## Verification

1. Run unit tests: `pytest tests/core/test_impl_folder.py -x`
2. Run impl collector tests: `pytest tests/unit/status/test_impl_collector.py -x`
3. Run full test suite: `make fast-ci`
4. Type check: `ty`
5. Manual: `erk implement <issue>` creates folder at `.erk/impl-context/<branch>/` with `plan.md` and `ref.json`

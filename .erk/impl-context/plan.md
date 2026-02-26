# Phase 1: Eliminate .impl/ folder references from source and tests

**Objective:** #8365 — Eliminate .impl/ Folder — Unify on .erk/impl-context/
**Nodes:** 1.1, 1.2, 1.3, 1.4

## Context

The codebase has two impl directory systems: legacy `.impl/` (flat, local) and modern `.erk/impl-context/<branch>/` (branch-scoped, committed). Most code already uses `resolve_impl_dir()` / `get_impl_dir()`, but 7 source files still hardcode `.impl` paths, and `impl_folder.py` retains legacy fallbacks for `.impl/` and `issue.json`. Phase 1 removes all of these.

## Execution Order

**Migrate callers first (1.2), then remove fallbacks (1.1), then cleanup (1.3), then tests (1.4).**

Removing fallbacks before migrating callers would break callers that still depend on `.impl/` resolution.

---

## Step A: Migrate hardcoded `.impl` paths (Node 1.2)

### A1. Delete `src/erk/core/workflow_display.py`

Module is **completely unused** — zero imports across the entire codebase, no test files. Delete the file.

### A2. `src/erk/cli/commands/pr/submit_pipeline.py` — `link_pr_to_objective_nodes()` (line 801)

`resolve_impl_dir` is already imported. `SubmitState` carries `branch_name`.

```python
# Replace lines 801-803:
impl_dir = resolve_impl_dir(state.cwd, branch_name=state.branch_name)
if impl_dir is None:
    return state
```

### A3. `src/erk/cli/commands/exec/scripts/objective_link_pr.py` — `_find_impl_dir()` (lines 36-52)

Delete the custom `_find_impl_dir()` function entirely. Replace with `resolve_impl_dir` from `erk_shared.impl_folder`. The function needs `branch_name`, obtainable via `require_git(ctx).branch.get_current_branch(cwd)`.

```python
# In objective_link_pr():
git = require_git(ctx)
current_branch = git.branch.get_current_branch(cwd)
impl_dir = resolve_impl_dir(cwd, branch_name=current_branch)
```

### A4. `src/erk/cli/commands/exec/scripts/setup_impl.py` — Path 3a auto-detect (line 196)

Currently checks `cwd / ".impl"` before obtaining git context. `git = require_git(ctx)` is at line 227. Move the git/branch detection before Path 3a and use `resolve_impl_dir()`:

```python
# Before Path 3: get git context
git = require_git(ctx)
current_branch = git.branch.get_current_branch(cwd)

# Path 3a: Check if impl already exists
impl_dir = resolve_impl_dir(cwd, branch_name=current_branch)
if impl_dir is not None:
    plan_ref = read_plan_ref(impl_dir)
    ...
```

Remove the duplicate `git = require_git(ctx)` at line 227.

### A5. `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` — Early exit check (line 130)

`git = require_git(ctx)` is already at line 125. Get branch name and use `resolve_impl_dir()`:

```python
current_branch = _get_current_branch(git, cwd)
impl_dir = resolve_impl_dir(cwd, branch_name=current_branch)
if impl_dir is not None:
    existing_ref = read_plan_ref(impl_dir)
    if existing_ref is not None and existing_ref.plan_id == str(plan_number):
        ...
```

### A6. `src/erk/cli/commands/wt/create_cmd.py` — `--copy-plan` (lines 642, 933-934)

**Validation (line 642):** Get current branch from git, use `resolve_impl_dir()`:

```python
if copy_plan:
    current_branch = git.branch.get_current_branch(repo.root)
    impl_source_check = resolve_impl_dir(repo.root, branch_name=current_branch)
    Ensure.truthy(ctx, impl_source_check is not None,
        f"No implementation directory found at {repo.root}. ...")
```

**Copy operation (lines 933-934):** Source from resolved dir, destination uses new branch name:

```python
if copy_plan:
    impl_source = resolve_impl_dir(repo.root, branch_name=current_branch)
    impl_dest = get_impl_dir(wt_path, branch_name=new_branch)
    impl_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(impl_source, impl_dest)
```

Need to verify `current_branch` and `new_branch` variable names in scope.

### A7. `src/erk/cli/commands/slot/common.py` — `cleanup_worktree_artifacts()` (lines 504, 508-509)

Remove the `.impl` cleanup lines. The function still cleans `.erk/impl-context/` and `.erk/scratch/`:

```python
def cleanup_worktree_artifacts(worktree_path: Path) -> None:
    impl_context_folder = worktree_path / IMPL_DIR_RELATIVE
    scratch_folder = worktree_path / ".erk" / "scratch"

    if impl_context_folder.exists():
        shutil.rmtree(impl_context_folder)
    if scratch_folder.exists():
        shutil.rmtree(scratch_folder)
```

---

## Step B: Remove legacy fallbacks from `impl_folder.py` (Node 1.1)

**File:** `packages/erk-shared/src/erk_shared/impl_folder.py`

### B1. `resolve_impl_dir()` — Delete Step 2 (lines 77-80)

Remove the legacy `.impl/` lookup and update the docstring.

### B2. `read_plan_ref()` — Delete `issue.json` fallback (lines 328-357)

Remove the entire block and update the docstring.

### B3. `has_plan_ref()` — Delete `issue.json` check (line 372)

Remove `or (impl_dir / "issue.json").exists()` and update the docstring.

---

## Step C: Health checks and init cleanup (Node 1.3)

### C1. `src/erk/core/health_checks.py` (line 674)

Remove `".impl/"` from `required_entries`.

### C2. `src/erk/cli/commands/init/main.py` (lines 229-234, 251)

Delete the `.impl/` gitignore prompt block. Remove `impl_added` from the condition on line 251.

---

## Step D: Update tests (Node 1.4)

For **each source file changed** in Steps A-B, update its corresponding test file:

| Source Change | Test File(s) |
|---|---|
| A2 (submit_pipeline) | `tests/unit/cli/commands/pr/submit_pipeline/test_link_pr_to_objective_nodes.py` |
| A3 (objective_link_pr) | `tests/unit/cli/commands/exec/scripts/test_objective_link_pr.py` |
| A4 (setup_impl) | `tests/unit/cli/commands/exec/scripts/test_setup_impl.py` |
| A5 (setup_impl_from_pr) | `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_pr.py` |
| A6 (create_cmd copy-plan) | `tests/commands/test_create_copy_impl.py` |
| A7 (slot cleanup) | `tests/unit/cli/commands/slot/test_assign_cmd.py` — delete `.impl` tests |
| B1-B3 (impl_folder.py) | `tests/packages/erk_shared/test_impl_folder.py` — delete legacy fallback tests, add non-regression test |
| C1 (health_checks) | `tests/core/test_health_checks.py` |
| C2 (init gitignore) | `tests/commands/setup/init/test_gitignore.py` |

**Additional standalone test files** needing `.impl` → `.erk/impl-context/<branch>/` migration:
- `tests/tui/data/test_provider.py`
- `tests/commands/test_dash_workflow_runs.py`
- `tests/commands/pr/test_dispatch.py`
- `tests/commands/pr/test_list.py`
- `tests/commands/pr/test_check.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_verify.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_init.py`
- `tests/unit/cli/commands/exec/scripts/test_upload_impl_session.py`
- `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py`
- `tests/unit/status/test_impl_collector.py`
- `tests/unit/status/test_orchestrator.py`

**Pattern:** Replace `tmp_path / ".impl"` with `get_impl_dir(tmp_path, branch_name="test-branch")` and add `.mkdir(parents=True)`.

---

## Verification

1. Run targeted tests after each step (A through D)
2. Full test suite: `make fast-ci`
3. Type check: `ty`
4. Lint: `ruff check`
5. Grep verify: `grep -r '\.impl["/]' src/ --include='*.py'` — should return zero results (excluding `impl_context`, `impl_folder`, `impl_verify`, `impl_init`, `impl_signal` in function/module names)
6. Grep verify tests: `grep -r 'tmp_path.*\.impl' tests/ --include='*.py'` — should return zero results

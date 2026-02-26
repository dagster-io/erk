# Plan: Update CLI commands to use resolve_impl_dir()

**Part of Objective #8197, Node 1.5**

## Context

Objective #8197 consolidates `.impl/` into branch-scoped `.erk/impl-context/<branch>/`. Nodes 1.1-1.4 are complete — the infrastructure (`resolve_impl_dir()`, `get_impl_dir()`) and exec scripts are migrated. Node 1.5 migrates the CLI commands that still hardcode `cwd / ".impl"`.

The migration pattern (established by PR #8279) is:
1. Get branch name from context: `ctx.git.branch.get_current_branch(cwd)`
2. Call `resolve_impl_dir(cwd, branch_name=branch_name)` instead of `cwd / ".impl"`
3. Handle `None` return (no impl folder found)

## Changes

### 1. `src/erk/cli/commands/pr/submit_pipeline.py`

**Line 136** — `prepare_state()`: Replace `impl_dir = cwd / ".impl"` with `resolve_impl_dir(cwd, branch_name=branch_name)`. `branch_name` is already available on line 123. Handle `None` — if `resolve_impl_dir` returns `None`, set `plan_id = None` and skip the auto-repair block (no impl dir to repair into). The auto-repair on line 148-160 should also only run if `impl_dir is not None`.

**Line 692** — `_finalize_pr()`: Replace `impl_dir = state.cwd / ".impl"` with `resolve_impl_dir(state.cwd, branch_name=state.branch_name)`. If `None`, `is_learn_plan()` returns `False` anyway (it checks file existence internally), so pass a sentinel or guard the call.

**Import**: Add `resolve_impl_dir` to the import from `erk_shared.impl_folder`.

**Comment/docstring updates**: Line 135 comment, line 148 comment.

### 2. `src/erk/cli/commands/pr/check_cmd.py`

**Line 265** — Replace `impl_dir = repo_root / ".impl"` with `resolve_impl_dir(repo_root, branch_name=branch)`. `branch` is available in the function scope (from the PR's head ref). Handle `None` — if no impl dir, `plan_ref` stays `None` (existing behavior for missing `.impl/`).

**Line 264 comment**: Update "`.impl always lives at worktree/repo root`" to reflect discovery-based resolution.

**Import**: Add `resolve_impl_dir` to imports from `erk_shared.impl_folder`.

### 3. `src/erk/cli/commands/pr/dispatch_cmd.py`

**Lines 422-451** — `_detect_plan_number_from_context()`: Replace dual-fallback chain with single `resolve_impl_dir()` call. The function currently takes `RepoContext` which doesn't have git gateway access. Options:
- Add `branch_name: str | None` parameter and pass from caller (line 510 where `original_branch` is available)
- This is cleaner than importing the git gateway into the helper

Updated function: `_detect_plan_number_from_context(repo: RepoContext, *, branch_name: str | None)` → calls `resolve_impl_dir(repo.root, branch_name=branch_name)`, then `read_plan_ref()`.

**Caller (line 510)**: Pass `branch_name=original_branch`.

**Docstring (line 471)**: Update help text from `.impl/, .erk/impl-context/` to reflect unified discovery.

### 4. `src/erk/cli/commands/pr/rewrite_cmd.py`

**Line 157** — Replace `impl_dir = cwd / ".impl"` with `resolve_impl_dir(cwd, branch_name=discovery.current_branch)`. `discovery.current_branch` is already in scope.

**Import**: Add `resolve_impl_dir` from `erk_shared.impl_folder`.

### 5. `src/erk/cli/commands/slot/common.py`

**Lines 502-506** — `cleanup_worktree_artifacts()`: Must clean up **both** legacy `.impl/` and any branch-scoped dirs under `.erk/impl-context/`. Replace hardcoded `.impl` cleanup with:
```python
impl_folder = worktree_path / ".impl"
impl_context_folder = worktree_path / IMPL_DIR_RELATIVE

if impl_folder.exists():
    shutil.rmtree(impl_folder)
if impl_context_folder.exists():
    shutil.rmtree(impl_context_folder)
```
This cleans the entire `.erk/impl-context/` directory (all branch subdirs) since we're recycling the worktree. Import `IMPL_DIR_RELATIVE` from `erk_shared.impl_folder`.

**Docstring**: Update to mention both paths.

### 6. `src/erk/cli/commands/pr/view_cmd.py` (docstrings only)

**Lines 233, 259, 269**: Update `.impl/plan-ref.json` references in user-facing messages and docstrings to say something like "plan reference file" or reference the new location.

### 7. `src/erk/cli/commands/implement.py` (docstrings only)

**Lines 1-9**: Update module docstring — `.impl/` references.
**Line 121**: Update dry-run description string.
**Lines 326, 335, 396, 399**: Update docstrings and error messages.

### 8. `src/erk/cli/commands/implement_shared.py` (docstrings only)

**Lines 457, 601, 672**: Update docstring references from `.impl/` to `.erk/impl-context/`.

### 9. `src/erk/cli/commands/wt/create_cmd.py` (docstring only)

**Line 434**: Update help text from `.impl/` to `.erk/impl-context/`.

## Key Files

- `packages/erk-shared/src/erk_shared/impl_folder.py` — `resolve_impl_dir()`, `IMPL_DIR_RELATIVE` (already exists, reuse)
- `src/erk/cli/commands/pr/submit_pipeline.py` — 2 hardcoded `.impl` paths
- `src/erk/cli/commands/pr/check_cmd.py` — 1 hardcoded `.impl` path
- `src/erk/cli/commands/pr/dispatch_cmd.py` — dual-fallback chain to consolidate
- `src/erk/cli/commands/pr/rewrite_cmd.py` — 1 hardcoded `.impl` path
- `src/erk/cli/commands/slot/common.py` — cleanup function needs both paths
- `src/erk/cli/commands/pr/view_cmd.py` — docstrings only
- `src/erk/cli/commands/implement.py` — docstrings/error messages only
- `src/erk/cli/commands/implement_shared.py` — docstrings only
- `src/erk/cli/commands/wt/create_cmd.py` — help text only

## Verification

1. Run `ruff check` and `ty check` on all modified files
2. Run existing tests for the modified commands:
   - `pytest tests/ -k "submit_pipeline or check_cmd or dispatch or rewrite or slot or implement or create_cmd"`
3. Grep for remaining hardcoded `.impl` references in `src/erk/cli/` to confirm none are missed
4. Manual sanity: `erk pr submit --dry-run` from a plan branch to verify prepare_state resolves correctly

# Consolidate DRY violations in checkout/impl-context code paths

## Context

PR #8830 extracted `create_impl_context_from_pr()` and added `erk pr prepare`, but left significant code duplication across the checkout and impl-context setup paths. This plan addresses 4 DRY violations to remove ~60 lines of duplicated logic.

## Changes

### 1. Extract `sync_parent_and_rebase()` into `checkout_helpers.py`

The "fetch parent branch, update stale local ref, rebase onto parent" sequence is duplicated verbatim between:
- `pr/checkout_cmd.py:261-290` (inline in `_checkout_pr`)
- `branch/checkout_cmd.py:372-398` (inside `_rebase_and_track_for_plan`)

**New function in `src/erk/cli/commands/checkout_helpers.py`:**

```python
def sync_parent_and_rebase(
    ctx: ErkContext,
    *,
    repo_root: Path,
    worktree_path: Path,
    parent_branch: str,
) -> None:
```

Encapsulates: list local branches → fetch parent → create tracking or update local ref → rebase onto parent → abort + warn on conflict. Uses `user_output` consistently.

**Does NOT include** Graphite tracking — that differs between callers (conditional track/retrack in PR checkout vs unconditional `track_branch` in branch checkout) and stays at call sites.

**Call site A — `pr/checkout_cmd.py` `_checkout_pr`:** Replace lines 261-290 with:
```python
trunk_branch = ctx.git.branch.detect_trunk_branch(repo.root)
if pr.base_ref_name != trunk_branch and not pr.is_cross_repository:
    sync_parent_and_rebase(ctx, repo_root=repo.root, worktree_path=worktree_path, parent_branch=pr.base_ref_name)
```

**Call site B — `branch/checkout_cmd.py` `_rebase_and_track_for_plan`:** Replace rebase body with:
```python
if parent_branch != trunk:
    sync_parent_and_rebase(ctx, repo_root=repo_root, worktree_path=worktree_path, parent_branch=parent_branch)
ctx.branch_manager.track_branch(repo_root, branch, parent_branch)
```

### 2. Add `find_existing_plan_ref()` to `impl_folder.py`

The idempotent "already set up?" check is duplicated between:
- `pr/prepare_cmd.py:69-75`
- `exec/scripts/setup_impl_from_pr.py:243-261`

**New function in `packages/erk-shared/src/erk_shared/impl_folder.py`:**

```python
def find_existing_plan_ref(
    base_path: Path,
    *,
    branch_name: str,
    plan_id: str,
) -> PlanRef | None:
```

Calls `resolve_impl_dir` → `read_plan_ref` → checks `ref.plan_id == plan_id` → returns `PlanRef` or `None`.

**Call site A — `prepare_cmd.py`:** Replace lines 69-75 with:
```python
existing_ref = find_existing_plan_ref(erk_ctx.cwd, branch_name=branch, plan_id=str(plan_number))
if existing_ref is not None:
    user_output(f"Impl-context already set up for plan #{plan_number}")
    return
```

**Call site B — `setup_impl_from_pr.py` `_setup_planned_pr_plan`:** Replace lines 244-247 with:
```python
existing_ref = find_existing_plan_ref(cwd, branch_name=current_branch, plan_id=str(plan_number))
if existing_ref is not None:
    # ... same early-return dict using existing_ref.url
```

### 3. Skip — `_setup_impl_for_plan` vs `create_impl_context_from_pr`

These have genuinely different data sources (`IssueBranchSetup` from plan store vs GitHub PR). The shared kernel is just two utility function calls (`create_impl_folder` + `save_plan_ref`), which is the correct level of abstraction. No further extraction.

### 4. Extract `_apply_plan_setup()` in `branch/checkout_cmd.py`

The `_rebase_and_track_for_plan` → `_setup_impl_for_plan` call pair is repeated 3x (lines 641-656, 676-690, 739-753).

**New private function in `branch/checkout_cmd.py`:**

```python
def _apply_plan_setup(
    ctx: ErkContext,
    *,
    setup: IssueBranchSetup,
    repo_root: Path,
    worktree_path: Path,
    branch: str,
    parent_branch: str,
    trunk: str,
    script: bool,
) -> None:
```

Calls `_rebase_and_track_for_plan` then `_setup_impl_for_plan`. Each call site's `if setup is not None:` guard remains at the call site.

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/checkout_helpers.py` | Add `sync_parent_and_rebase()` |
| `packages/erk-shared/src/erk_shared/impl_folder.py` | Add `find_existing_plan_ref()` |
| `src/erk/cli/commands/pr/checkout_cmd.py` | Use `sync_parent_and_rebase` in `_checkout_pr` |
| `src/erk/cli/commands/branch/checkout_cmd.py` | Use `sync_parent_and_rebase` in `_rebase_and_track_for_plan`; extract `_apply_plan_setup`; collapse 3 call sites |
| `src/erk/cli/commands/pr/prepare_cmd.py` | Use `find_existing_plan_ref` |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` | Use `find_existing_plan_ref` |

## Verification

1. Run checkout tests: `pytest tests/commands/pr/test_checkout.py tests/commands/pr/test_checkout_graphite_linking.py`
2. Run branch checkout tests: `pytest tests/commands/branch/test_checkout_cmd.py`
3. Run prepare tests: `pytest tests/commands/pr/test_prepare.py`
4. Run setup-impl tests: `pytest tests/unit/cli/commands/exec/scripts/test_setup_impl_from_pr.py`
5. Run impl_folder tests: `pytest tests/ -k impl_folder`
6. `ty` type check passes

# Fix: `create_worker_impl_folder` crashes on re-submission

## Context

When re-submitting a draft-PR plan via `erk plan submit` (e.g., from the TUI), the command crashes with `FileExistsError` because `.worker-impl/` already exists on the branch from a prior submission. This can happen when:
- A previous submission's workflow failed and left `.worker-impl/` on the branch
- The user re-submits a plan that was already submitted

The workflow (`plan-implement.yml`) cleans up `.worker-impl/` during execution, but the submit command doesn't handle the case where it already exists on the local checkout.

Note: `.worker-impl/` (committed to git, queue visibility) and `.impl/` (local-only, Claude's working copy) are architecturally distinct and both necessary. This is just a missing cleanup in the submit path.

## Fix

Add cleanup of existing `.worker-impl/` before calling `create_worker_impl_folder()` in both call sites in `submit.py`. This mirrors the workflow's own `rm -rf .worker-impl` cleanup pattern.

### `src/erk/cli/commands/submit.py`

1. **Update import** (line 47): Add `remove_worker_impl_folder` and `worker_impl_folder_exists` to the import from `erk_shared.worker_impl_folder`

2. **Draft-PR path** (before line 436): After `checkout_branch` and before `create_worker_impl_folder`, add:
   ```python
   if worker_impl_folder_exists(repo.root):
       user_output("Cleaning up previous .worker-impl/ folder...")
       remove_worker_impl_folder(repo.root)
   ```

3. **Issue-based path** (before line 704): Same cleanup pattern before the second `create_worker_impl_folder` call at line 705.

### No changes needed to `worker_impl_folder.py`

The `FileExistsError` is correct defensive behavior — the caller should handle the pre-existing state.

## Verification

- Run existing tests for `worker_impl_folder`: `pytest tests/ -k worker_impl`
- Run existing tests for submit: `pytest tests/ -k submit`
- Run fast-ci to check nothing else breaks

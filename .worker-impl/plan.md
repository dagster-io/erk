# Plan: Support `quick-submit` Without Graphite

## Summary

Make `erk exec quick-submit` work when Graphite is disabled by using `git push` instead of `gt submit`.

## Context

`quick-submit` currently always uses `gt submit` which fails when Graphite is disabled. The pattern for checking config in exec scripts is established in `session_id_injector_hook.py` - use `RealErkInstallation` directly.

## Changes

### 1. Update `quick_submit.py` to check Graphite availability

**File:** `src/erk/cli/commands/exec/scripts/quick_submit.py`

Add a helper function:
```python
def _is_graphite_enabled() -> bool:
    """Check if Graphite is enabled in ~/.erk/config.toml."""
    installation = RealErkInstallation()
    if not installation.config_exists():
        return False  # Default disabled
    config = installation.load_config()
    return config.use_graphite and shutil.which("gt") is not None
```

Pass this to `execute_quick_submit()`.

### 2. Update `execute_quick_submit` to support non-Graphite path

**File:** `packages/erk-shared/src/erk_shared/gateway/gt/operations/quick_submit.py`

Add parameter `use_graphite: bool` to the function signature.

Change step 4 logic:
```python
if use_graphite:
    # Step 4a: Run gt submit
    yield ProgressEvent("Submitting to Graphite...")
    ops.graphite.submit_stack(repo_root, quiet=True, force=True)
else:
    # Step 4b: Run git push
    yield ProgressEvent("Pushing to remote...")
    current_branch = ops.git.get_current_branch(cwd)
    if current_branch:
        ops.git.push_to_remote(repo_root, "origin", current_branch, set_upstream=True, force=True)
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/erk/cli/commands/exec/scripts/quick_submit.py` | Add Graphite check, pass boolean to operation |
| `packages/erk-shared/src/erk_shared/gateway/gt/operations/quick_submit.py` | Add `use_graphite` param, conditional git push using existing `git.push_to_remote()` |

Note: `git.push_to_remote()` already exists in `packages/erk-shared/src/erk_shared/git/abc.py:551` with `force` flag support.

## Testing

- Test quick-submit with Graphite enabled (existing behavior)
- Test quick-submit with Graphite disabled (uses git push)
# Fix: `erk plan submit` hanging with no output

## Context

`erk plan submit 8022` hangs indefinitely with no output. The root cause is twofold:

1. **No progress output**: The command performs ~8 blocking subprocess/network operations before the first `user_output` at line 1261. Users see nothing and think the command is deadlocked.
2. **Missing timeouts**: Three subprocess calls use `subprocess.run()` with no timeout, meaning they can block forever.

## Changes

### 1. Add progress output before each blocking operation in `submit_cmd`

**File:** `src/erk/cli/commands/submit.py` (lines 1148-1217)

Add `user_output()` before each blocking call:

```python
# Line ~1148: Before gh auth check
user_output("Checking GitHub authentication...")
Ensure.gh_authenticated(ctx)

# Line ~1157: Before trunk sync (includes git fetch)
user_output("Syncing trunk with remote...")
ensure_trunk_synced(ctx, repo)

# Line ~1189: Before issue existence check (gh api call)
# (only when single issue + no --base)
user_output(f"Checking issue #{issue_number}...")
if (
    issue_number is not None
    and base is None
    and ctx.issues.issue_exists(repo.root, issue_number)
):
    ...

# Line ~1212: Before second auth status call
user_output("Resolving GitHub username...")
_, username, _ = ctx.github.check_auth_status()
```

The fast/local calls (get_current_branch, detect_trunk_branch, branch_exists_on_remote) don't need output — they're purely local git operations.

### 2. Add timeout to `issue_exists`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py:126-132`

Replace raw `subprocess.run()` with `run_subprocess_with_context()`:

```python
result = run_subprocess_with_context(
    cmd=cmd,
    operation_context=f"check if issue #{number} exists",
    cwd=repo_root,
    capture_output=True,
    check=False,
    timeout=_GH_COMMAND_TIMEOUT,
)
```

Import `run_subprocess_with_context` and `_GH_COMMAND_TIMEOUT` from `erk_shared.subprocess_utils`.

### 3. Add timeout to `get_current_username`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py:539-544`

Same pattern — replace raw `subprocess.run()` with `run_subprocess_with_context()`:

```python
result = run_subprocess_with_context(
    cmd=["gh", "api", "user", "--jq", ".login"],
    operation_context="get current GitHub username",
    capture_output=True,
    check=False,
    timeout=_GH_COMMAND_TIMEOUT,
)
```

### 4. Add timeout to `check_auth_status`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/real.py:1024-1029`

Add `timeout=` to the existing `run_subprocess_with_context()` call:

```python
result = run_subprocess_with_context(
    cmd=["gh", "auth", "status"],
    operation_context="check GitHub authentication status",
    capture_output=True,
    check=False,
    timeout=_GH_COMMAND_TIMEOUT,  # ADD THIS
)
```

Import `_GH_COMMAND_TIMEOUT` from `erk_shared.subprocess_utils`.

## Files Modified

- `src/erk/cli/commands/submit.py` — add progress output
- `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py` — add timeouts to `issue_exists` and `get_current_username`
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` — add timeout to `check_auth_status`

## Verification

1. Run existing tests: `pytest tests/ -k "submit"` to confirm no regressions
2. Run `erk plan submit <number>` — should show step-by-step progress immediately
3. If `gh` is unresponsive, should fail with a timeout error after 60s instead of hanging forever

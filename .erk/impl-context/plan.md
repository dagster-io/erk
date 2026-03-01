# Fix: `erk pr submit` silent hang with no output

## Context

When `erk pr submit` runs from Claude Code's Bash tool, it hangs silently for 2 minutes with **no visible output** before timing out. This happens because:

1. **Silent pipeline steps**: The first 4 pipeline steps (`prepare_state`, `cleanup_impl_for_submit`, `commit_wip`, `capture_existing_pr_body`) produce no output, so users see nothing while potentially slow git/GitHub operations run.
2. **No centralized flushing**: When stdout is piped (as in Bash tool), output may buffer at the OS level even though `click.echo()` calls `file.flush()`. A belt-and-suspenders `sys.stdout.flush()` after each step ensures visibility.
3. **Missing timeouts**: `check_auth_status()` and `is_branch_tracked()` in the Graphite gateway use raw `subprocess.run` with **no timeout**, meaning they can hang indefinitely on network issues.

## Changes

### 1. Add `sys.stdout.flush()` in `submit_cmd.py` after banner

**File**: `src/erk/cli/commands/pr/submit_cmd.py`

- Add `import sys`
- Add `sys.stdout.flush()` after lines 170-171 ("🚀 Submitting PR...")

### 2. Add centralized flush in pipeline runners

**File**: `src/erk/cli/commands/pr/submit_pipeline.py`

Add `sys.stdout.flush()` after each step completes in both `run_submit_pipeline()` and `run_push_and_create_pipeline()`. This ensures every step's output is visible regardless of buffering.

### 3. Add progress messages for silent steps

**File**: `src/erk/cli/commands/pr/submit_pipeline.py`

Add dimmed progress messages (matching existing style) to:
- `prepare_state`: `"   Resolving branch and plan context..."`
- `capture_existing_pr_body`: `"   Checking for existing PR..."`

Skip `cleanup_impl_for_submit` (early-returns in most cases, adding a message would be noise).

### 4. Add timeouts to Graphite subprocess calls

**File**: `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`

- `check_auth_status()` (line 169): Add `timeout=15` and catch `TimeoutExpired` → return `(False, None, None)`
- `is_branch_tracked()` (line 278): Add `timeout=15` and catch `TimeoutExpired` → return `False`

Both timeouts use safe defaults (treat timeout as "not available") so the command degrades gracefully instead of hanging.

## Files to modify

- `src/erk/cli/commands/pr/submit_cmd.py` - import + flush
- `src/erk/cli/commands/pr/submit_pipeline.py` - runner flushes + progress messages
- `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` - subprocess timeouts

## Verification

1. Run `make fast-ci` to verify existing tests pass
2. Run `erk pr submit --skip-description` from a branch with changes to verify progress output appears
3. The new progress messages should be visible even when piped: `erk pr submit --skip-description 2>&1 | cat`

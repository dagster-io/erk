# Plan: Add Progress Feedback to Async Learn Trigger

## Problem

When running `erk land`, after printing "Triggering async learn for plan #5602..." there's a noticeable hang (potentially up to 25 seconds) before the success message appears. The user has no feedback about what's happening during this time.

## Root Cause Analysis

1. `trigger_workflow()` in `packages/erk-shared/src/erk_shared/github/real.py:287-420` polls GitHub API up to 15 times waiting for the workflow run to appear (5×1s + 10×2s = up to 25 seconds worst case)

2. `trigger_async.py` already has `on_progress` callback infrastructure with progress messages:
   - "Fetching issue #..."
   - "Validating plan metadata..."
   - "Triggering workflow..."
   - "Waiting for workflow to appear..."
   - "Updating plan status..."

3. BUT the exec script `trigger_async_learn.py` passes `on_progress=None` (line 81)

4. AND `land_cmd.py` uses `capture_output=True` which would capture any output anyway

## Implementation Approach

### Step 1: Update exec script to emit progress to stderr

**File**: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

Pass a callback that writes progress to stderr (so it doesn't interfere with JSON output on stdout):

```python
result = trigger_async_learn_workflow(
    github=github,
    issues=github_issues,
    repo_root=repo_root,
    issue_number=issue_number,
    on_progress=lambda msg: click.echo(msg, err=True),
)
```

### Step 2: Update land command to stream stderr while capturing stdout

**File**: `src/erk/cli/commands/land_cmd.py`

Change from `subprocess.run(..., capture_output=True)` to using `Popen` that streams stderr in real-time while capturing stdout for JSON parsing:

```python
# Instead of capture_output=True, stream stderr while capturing stdout
process = subprocess.Popen(
    ["erk", "exec", "trigger-async-learn", str(plan_issue_number)],
    stdout=subprocess.PIPE,
    stderr=None,  # Inherit stderr - progress streams through
    text=True,
    cwd=ctx.cwd,
)
stdout, _ = process.communicate()
```

## Critical Files

- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:76-82` - Add progress callback
- `src/erk/cli/commands/land_cmd.py:268-275` - Change subprocess handling

## User Experience After Change

```
$ erk land
Warning: Plan #5602 has not been learned from.
...
Triggering async learn for plan #5602...
  Fetching issue #5602...
  Validating plan metadata...
  Triggering workflow...
  Waiting for workflow to appear...
  Updating plan status...
✓ Async learn triggered: https://github.com/...
```

## Verification

1. Run `erk land` on a PR with a plan that hasn't been learned
2. Observe progress messages streaming during the async learn trigger
3. Verify JSON parsing still works (success message with URL appears)
4. Test error cases still work (e.g., issue not found, not an erk-plan)
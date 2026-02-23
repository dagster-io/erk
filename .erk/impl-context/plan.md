# Preemptive CLAUDE_ENABLED check in async learn pipeline

## Context

When `CLAUDE_ENABLED` is set to `'false'` as a GitHub repo variable, the `learn.yml` workflow's job is skipped via a `if: vars.CLAUDE_ENABLED != 'false'` condition. Currently, `erk land` triggers the full learn pipeline (session discovery, preprocessing, branch commit, workflow dispatch) and then waits 30+ seconds polling for the workflow run, only to get an error like:

```
⚠ Could not trigger async learn: Failed to trigger workflow: Workflow 'learn.yml' run was skipped.
```

The fix: check `CLAUDE_ENABLED` at the very start of the exec script and skip the entire pipeline immediately with a clear warning, avoiding all wasted work.

**User constraint**: Only skip when the variable is **explicitly** set to `'false'`. If unset (`None`) or any other value, proceed normally.

## Changes

### 1. Add early CLAUDE_ENABLED check in `trigger_async_learn.py`

**File**: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

After context validation (line ~382, after `plan_backend = require_plan_backend(ctx)`), add:

```python
# Check if CLAUDE_ENABLED is explicitly disabled before doing any work
location = GitHubRepoLocation(
    root=repo_root,
    repo_id=GitHubRepoId(owner=repo_info.owner, repo=repo_info.name),
)
claude_enabled_value = ctx.obj.github_admin.get_variable(location, "CLAUDE_ENABLED")
if claude_enabled_value == "false":
    click.echo(
        click.style("⚠ ", fg="yellow")
        + "CLAUDE_ENABLED is explicitly set to 'false' — skipping learn workflow",
        err=True,
    )
    _output_error("CLAUDE_ENABLED is explicitly set to 'false' — skipping learn workflow")
    return
```

Add imports:
- `GitHubRepoId`, `GitHubRepoLocation` from `erk_shared.gateway.github.types`

### 2. Add test for CLAUDE_ENABLED skip

**File**: `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`

Add a test that:
- Creates `FakeGitHubAdmin(variables={"CLAUDE_ENABLED": "false"})`
- Passes it to `ErkContext.for_test(github_admin=...)`
- Invokes `trigger_async_learn` command
- Asserts exit code is 1 (error path)
- Asserts JSON output has `"success": false` with `"CLAUDE_ENABLED"` in the error message
- Asserts no workflows were triggered on `FakeGitHub`

Also add a test that verifies unset (`None`) does NOT skip:
- Use default `FakeGitHubAdmin()` (empty variables dict)
- Verify the pipeline proceeds normally (existing tests already cover this implicitly, but an explicit test is clearer)

## Files to modify

1. `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — add early check + imports
2. `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py` — add 2 tests

## Verification

1. Run scoped tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`
2. Run ty/ruff checks on modified files

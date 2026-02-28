# Add "rewrite" TUI command (rebase + AI PR summary)

## Context

Currently there's no single command in the TUI to rebase a PR off master and regenerate its summary. This requires manually running `erk launch pr-fix-conflicts` then separately triggering a rewrite. Adding a unified "rewrite" command combines both steps into one remote workflow, triggered from the TUI command palette.

## Implementation

### 1. New GitHub Actions workflow: `.github/workflows/pr-rewrite.yml`

Create based on `pr-fix-conflicts.yml` with these differences:
- **No squash step** before rebase (`erk pr rewrite` handles squashing in its own pipeline)
- **Add `erk pr rewrite` step** after the rebase step
- Concurrency group: `rewrite-${{ github.event.inputs.branch_name }}`
- Status comment says "Remote rewrite" instead of "Remote rebase"

Workflow inputs (same as pr-fix-conflicts minus `squash`):
- `branch_name`, `base_branch`, `pr_number`, `distinct_id`, `model_name`, `plan_number`

Steps:
1. Checkout repo (fetch-depth: 0)
2. `erk-remote-setup` action
3. Write dispatch metadata to plan (if plan_number set)
4. Checkout target branch
5. `erk exec rebase-with-conflict-resolution` (rebase onto base_branch, no prior squash)
6. **`erk pr rewrite`** (squash + AI message + amend + force push + update PR)
7. Post status comment to PR
8. Update plan header with dispatch metadata

### 2. Add to workflow map: `src/erk/cli/constants.py`

Add constant and map entry:
```python
PR_REWRITE_WORKFLOW_NAME = "pr-rewrite.yml"
```
Add `"pr-rewrite": PR_REWRITE_WORKFLOW_NAME` to `WORKFLOW_COMMAND_MAP`.

### 3. Add launch handler: `src/erk/cli/commands/launch_cmd.py`

Add `_trigger_pr_rewrite()` after `_trigger_pr_address()` (~line 180). Follow the `_trigger_pr_address` pattern:
- Require `--pr` (no auto-detect from current branch)
- Validate PR is OPEN
- Build inputs: `branch_name`, `base_branch`, `pr_number`, `plan_number`, optional `model_name`
- Call `_trigger_workflow()` with `workflow_name="pr-rewrite"`

Add dispatch branch in `launch()` after `pr-address` branch (~line 328):
```python
elif workflow_name == "pr-rewrite":
    Ensure.invariant(pr_number is not None, "--pr is required for pr-rewrite workflow")
    assert pr_number is not None
    _trigger_pr_rewrite(ctx, repo, pr_number=pr_number, model=model)
```

Update docstring to list `pr-rewrite` in available workflows.

### 4. TUI registry: `src/erk/tui/commands/registry.py`

Add two display name generators (after `_display_copy_address_remote`):
- `_display_rewrite_remote(ctx)` -> `f"erk launch pr-rewrite --pr {ctx.row.pr_number}"`
- `_display_copy_rewrite_remote(ctx)` -> same string

Add two CommandDefinitions:
- **ACTION** `rewrite_remote`: description="rewrite", shortcut=None, available when plan view + pr_number is not None
- **COPY** `copy_rewrite_remote`: description="rewrite", shortcut=None, same availability

### 5. TUI main app handler: `src/erk/tui/app.py`

Add `_rewrite_remote_async()` method following `_fix_conflicts_remote_async` pattern:
- `@work(thread=True)`
- Runs `["erk", "launch", "pr-rewrite", "--pr", str(pr_number)]` via `_run_streaming_operation`
- Toast notifications on success/failure
- Triggers `action_refresh` on success

Add two branches in `execute_palette_command()`:
- `"rewrite_remote"` -> start operation + call `_rewrite_remote_async`
- `"copy_rewrite_remote"` -> copy command to clipboard

### 6. TUI detail screen handler: `src/erk/tui/screens/plan_detail_screen.py`

Add two branches in `execute_command()`:
- `"rewrite_remote"` -> dismiss + delegate to `self.app._rewrite_remote_async()` (follows `fix_conflicts_remote` pattern)
- `"copy_rewrite_remote"` -> copy command to clipboard

### 7. Registry tests: `tests/tui/commands/test_registry.py`

Add tests following existing fix_conflicts/address patterns:
- `test_rewrite_remote_available_when_pr_exists`
- `test_rewrite_remote_not_available_when_no_pr`
- `test_copy_rewrite_remote_available_when_pr_exists`
- `test_copy_rewrite_remote_not_available_when_no_pr`
- `test_display_name_rewrite_remote_shows_cli_command`
- `test_display_name_copy_rewrite_remote_shows_cli_command`

Update existing test lists:
- `test_plan_commands_hidden_in_objectives_view`: add `"rewrite_remote"` and `"copy_rewrite_remote"` to `plan_cmd_ids`
- `test_commands_available_in_plans_view`: add `"rewrite_remote"` and `"copy_rewrite_remote"` to `expected_available`

## Key files

| File | Change |
|------|--------|
| `.github/workflows/pr-rewrite.yml` | New workflow |
| `src/erk/cli/constants.py` | Add constant + map entry |
| `src/erk/cli/commands/launch_cmd.py` | Add handler + dispatch branch |
| `src/erk/tui/commands/registry.py` | Add 2 display generators + 2 CommandDefinitions |
| `src/erk/tui/app.py` | Add async method + 2 palette handler branches |
| `src/erk/tui/screens/plan_detail_screen.py` | Add 2 handler branches |
| `tests/tui/commands/test_registry.py` | Add 6 tests + update 2 existing lists |

## Verification

1. Run registry tests: `uv run pytest tests/tui/commands/test_registry.py`
2. Run full fast CI: `make fast-ci`
3. Manual TUI verification: `erk dash -i`, select a PR row, open command palette, confirm "rewrite" appears with correct display

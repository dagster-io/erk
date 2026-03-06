# Add /erk:pr-incremental-dispatch — Dispatch Local Plan Against Existing PR

## Context

When iterating on an existing PR, it's natural to plan additional changes and dispatch them for remote implementation — without creating a separate planned PR. Currently this requires creating a new planned PR (#8784) and later squashing it into the original PR (#8778).

This plan adds `/erk:pr-incremental-dispatch`, a slash command (plus supporting CLI/workflow changes) that lets you write a plan in plan mode and dispatch it directly against an existing PR's branch.

## Architecture

Three changes needed:

### 1. Workflow: Support pre-committed impl-context

**File**: `.github/workflows/plan-implement.yml` (lines 147-158)

Current flow always deletes and re-creates impl-context from the plan store (PR body). Change to check if `plan.md` already exists on the branch first:

```yaml
if [ -f .erk/impl-context/plan.md ]; then
  echo "Using pre-committed impl-context from branch"
else
  rm -rf .erk/impl-context
  erk exec create-impl-context-from-plan "$PLAN_ID"
  # ... existing error handling ...
fi
```

This is the minimal change that unblocks the entire feature. When the slash command pre-commits the plan to `.erk/impl-context/plan.md` on the branch, the workflow uses it directly instead of trying to parse the PR body.

### 2. CLI: `erk exec incremental-dispatch`

**New file**: `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`

A new exec script that takes a `--plan-file` and `--pr` number and:
1. Validates PR exists and is OPEN (no label check — reuse `ctx.github.get_pr()`)
2. Reads plan content from the file
3. Builds impl-context files via `build_impl_context_files()` from `erk_shared.impl_context`
4. Commits to the branch using `ctx.git.commit.commit_files_to_branch()` (git plumbing, no checkout needed)
5. Pushes to remote
6. Triggers `plan-implement.yml` workflow via `ctx.github.trigger_workflow()`

**Reuse from dispatch_cmd.py**:
- `load_workflow_config()` for workflow-specific config
- `ensure_trunk_synced()` from `dispatch_helpers.py`
- `_build_workflow_run_url()` for URL construction
- Pattern from `_dispatch_planned_pr_plan()` lines 208-355 (the core dispatch logic)

**Register in**: `src/erk/cli/commands/exec/group.py`

Key differences from `_dispatch_planned_pr_plan`:
- Plan content comes from `--plan-file` (local file) instead of `ctx.plan_store.get_plan()`
- No `erk-plan` label validation — just check PR exists and is OPEN
- Uses the PR's existing branch (from `pr.head_ref_name`)

Click interface:
```python
@click.command(name="incremental-dispatch")
@click.option("--plan-file", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--pr", type=int, required=True)
@click.option("--ref", default=None)  # workflow dispatch ref
@click.option("--format", "output_format", type=click.Choice(["json", "display"]), default="json")
@click.pass_context
```

JSON output:
```json
{
  "success": true,
  "pr_number": 8778,
  "branch_name": "plnd/objective-nodes-screen-03-05-1119",
  "workflow_run_id": "1234567890",
  "workflow_url": "https://github.com/..."
}
```

### 3. Slash command: `/erk:pr-incremental-dispatch`

**New file**: `.claude/commands/erk/pr-incremental-dispatch.md`

Steps the command instructs Claude to perform:
1. **Find the plan**: Search session for the plan file (same as plan-save — use `.claude/plans/` most recent file)
2. **Get PR context**: Run `gh pr view --json number,title,headRefName` to get current branch's PR. If `$ARGUMENTS` contains a PR number, use that instead.
3. **Confirm with user**: Show "Dispatching plan against PR #NNNN (branch: xxx). Proceed?"
4. **Run dispatch**: `erk exec incremental-dispatch --plan-file <path> --pr <number> --format json`
5. **Display results**: Show PR URL and workflow URL

## Files to Create/Modify

| File | Action |
|------|--------|
| `.github/workflows/plan-implement.yml` | Modify: add impl-context pre-commit check |
| `src/erk/cli/commands/exec/scripts/incremental_dispatch.py` | Create: new exec command |
| `src/erk/cli/commands/exec/group.py` | Modify: register new command |
| `.claude/commands/erk/pr-incremental-dispatch.md` | Create: slash command |

## Verification

1. Write a plan in plan mode for an existing PR
2. Run `/erk:pr-incremental-dispatch`
3. Verify: impl-context committed to branch, workflow triggered, workflow uses pre-committed plan
4. Unit tests for `incremental_dispatch.py` using fake gateways

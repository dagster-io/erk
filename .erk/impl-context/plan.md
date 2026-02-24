# Fix objective update after landing for plnd/ branches

## Context

When `erk land` landed PR #8070 for objective #8036, the objective update failed. The agent fell back to manual body editing, creating inconsistencies between YAML (issue body) and comment table.

**Root cause:** In `_execute_land_directly` (`land_cmd.py:1343`), the objective update runs AFTER the execution pipeline, which merges the PR and deletes the branch. By then, `get_objective_for_branch` → `plan_backend.get_plan_for_branch()` may fail because the branch is deleted. Even if `get_pr_for_branch` still finds the PR (GitHub retains head ref), the timing creates fragility. And when `run_objective_update_after_land` invokes the Claude command, the command's `erk exec objective-apply-landed-update` tries to look up the plan from the branch again, creating a second failure point.

The navigation mode (`_land_target`) doesn't have this bug because it captures `objective_number` BEFORE generating the execution script, while the branch still exists.

**What the user saw:** The agent used `objective-fetch-context` (wrong script), got empty `matched_steps`, tried `update-objective-node` (failed), then fell back to manual `gh` commands that partially updated the YAML but not the comment table.

## Changes

### 1. Capture plan_id and objective BEFORE execution pipeline

**File:** `src/erk/cli/commands/land_cmd.py` — `_execute_land_directly`

Move `get_objective_for_branch` call and add `plan_id` capture BEFORE `run_execution_pipeline`:

```python
# Capture plan context BEFORE execution pipeline (which deletes the branch)
plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, branch)
objective_number = get_objective_for_branch(ctx, main_repo_root, branch)

# Run execution pipeline (merge + cleanup)
...

# Objective update (fail-open — merge already succeeded)
if objective_number is not None:
    run_objective_update_after_land(
        ctx,
        objective=objective_number,
        pr=pr_number,
        branch=branch,
        plan=int(plan_id) if plan_id is not None else None,
    )
```

### 2. Add `plan` parameter to `run_objective_update_after_land`

**File:** `src/erk/cli/commands/objective_helpers.py`

Add optional `plan: int | None` parameter. When provided, include `--plan {plan}` in the command:

```python
def run_objective_update_after_land(
    ctx: ErkContext,
    *,
    objective: int,
    pr: int,
    branch: str,
    plan: int | None,
) -> None:
    plan_arg = f" --plan {plan}" if plan is not None else ""
    cmd = (
        f"/erk:objective-update-with-landed-pr "
        f"--pr {pr} --objective {objective} --branch {branch}{plan_arg} --auto-close"
    )
```

Update all 3 call sites:
- `land_cmd.py:1346` — pass `plan=int(plan_id) if plan_id else None`
- `land_execute.py:174` — pass `plan=plan_number` (new parameter)
- `objective_update_after_land.py:53` — pass `plan=plan_number` (new parameter)

### 3. Add `--plan` to `land_execute.py`

**File:** `src/erk/cli/commands/exec/scripts/land_execute.py`

Add `--plan-number` option (matches existing `--objective-number` pattern):

```python
@click.option(
    "--plan-number",
    type=int,
    help="Linked plan issue number",
)
```

Pass through to `run_objective_update_after_land(... plan=plan_number)`.

### 4. Add `--plan` to `objective-apply-landed-update`

**File:** `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

Add `--plan` option:

```python
@click.option(
    "--plan",
    "plan_number",
    type=int,
    default=None,
    help="Plan number (direct lookup, skips branch-based discovery)",
)
```

In the discovery logic (around line 190), add direct lookup path (mirror `objective_fetch_context.py:170-175`):

```python
if plan_number is not None:
    plan_result = plan_backend.get_plan(repo_root, str(plan_number))
    if isinstance(plan_result, PlanNotFound):
        click.echo(_error_json(f"Plan #{plan_number} not found"))
        raise SystemExit(1)
else:
    # Existing branch-based discovery
    plan_result = plan_backend.get_plan_for_branch(repo_root, branch_name)
    if isinstance(plan_result, PlanNotFound):
        click.echo(_error_json(f"No plan found for branch '{branch_name}'"))
        raise SystemExit(1)
```

### 5. Pass `plan_number` through script generation

**File:** `src/erk/cli/commands/land_cmd.py` — `_land_target`

Capture `plan_id` alongside `objective_number` (line ~1426):

```python
plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, branch)
objective_number = get_objective_for_branch(ctx, main_repo_root, branch)
```

Pass `plan_number` to `render_land_execution_script`.

**File:** `src/erk/cli/commands/land_cmd.py` — `render_land_execution_script`

Add `plan_number` parameter and include `--plan-number` in generated script.

### 6. Update command definition

**File:** `.claude/commands/erk/objective-update-with-landed-pr.md`

Update Step 1 to document `--plan`:

```bash
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--plan <number>] [--branch <name>]
```

Add note: `--plan` enables direct plan lookup, avoiding branch-based discovery which may fail after branch deletion.

### 7. Fix current inconsistent state on #8036

After the code fix, run:
```bash
erk exec update-objective-node 8036 --node 1.2 --plan "#8070" --pr "#8070" --status done
```
This will sync the comment table with the YAML.

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/land_cmd.py` | Capture plan_id before execution, pass to helpers |
| `src/erk/cli/commands/objective_helpers.py` | Add `plan` parameter to `run_objective_update_after_land` |
| `src/erk/cli/commands/exec/scripts/land_execute.py` | Add `--plan-number` option |
| `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py` | Add `--plan` option with direct lookup |
| `src/erk/cli/commands/exec/scripts/objective_update_after_land.py` | Add `--plan-number` option |
| `.claude/commands/erk/objective-update-with-landed-pr.md` | Document `--plan` option |
| Script template (`render_land_execution_script`) | Pass plan_number through |

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
2. Run existing land tests: `pytest tests/unit/cli/commands/test_land_cmd.py`
3. Add test for `--plan` direct lookup path in `test_objective_apply_landed_update.py`
4. Verify `erk exec objective-apply-landed-update --help` shows `--plan` option
5. Fix #8036 state: `erk exec update-objective-node 8036 --node 1.2 --plan "#8070" --pr "#8070" --status done`

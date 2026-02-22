# Add `--plan-only` flag to `erk one-shot`

## Context

`erk one-shot` dispatches a GitHub Actions workflow (`one-shot.yml`) that runs two jobs:
1. **plan** — Claude explores the codebase and saves a plan to a GitHub issue
2. **implement** — Claude implements the plan and commits the code

There's currently no way to run only the planning phase remotely. The user wants a command that goes from prompt → plan without triggering implementation.

## Approach

Add `--plan-only` to `erk one-shot`. When set, it passes `plan_only=true` as a workflow input. The `one-shot.yml` implement job gains a condition that skips it when `plan_only` is true.

This is a 2-file change that follows the existing `extra_workflow_inputs` pattern (same mechanism used by `erk objective plan --one-shot` to pass `objective_issue` and `node_id`).

## Changes

### 1. `src/erk/cli/commands/one_shot.py`

Add `--plan-only` Click option:

```python
@click.option(
    "--plan-only",
    is_flag=True,
    help="Create a plan remotely without implementing it",
)
```

Add `plan_only: bool` to the function signature.

Update `OneShotDispatchParams` construction to include it in `extra_workflow_inputs`:

```python
extra: dict[str, str] = {}
if plan_only:
    extra["plan_only"] = "true"
params = OneShotDispatchParams(
    prompt=prompt,
    model=model,
    extra_workflow_inputs=extra,
)
```

Update the docstring with an example:
```
erk one-shot "rename issue_number to plan_number in impl_init.py" --plan-only
```

### 2. `.github/workflows/one-shot.yml`

Add `plan_only` boolean input to `workflow_dispatch.inputs`:

```yaml
plan_only:
  description: "If true, only run the plan phase, skip implementation"
  required: false
  type: boolean
  default: false
```

Update the `implement` job condition (line 225) from:

```yaml
if: needs.plan.outputs.plan_id != ''
```

to:

```yaml
if: needs.plan.outputs.plan_id != '' && !inputs.plan_only
```

## Files to Modify

- `src/erk/cli/commands/one_shot.py` — add `--plan-only` flag
- `.github/workflows/one-shot.yml` — add input, update implement job condition

## Files NOT Changing

- `one_shot_dispatch.py` — `extra_workflow_inputs` already passes arbitrary keys through to the workflow; no changes needed
- `plan-implement.yml` — implement workflow is unchanged; it just won't be called
- Any tests — no test exists for `one_shot.py` dispatch (it's integration-heavy CLI)

## Verification

```bash
# Dry-run to confirm flag is accepted and shown
erk one-shot "test prompt" --plan-only --dry-run
# Should print: Extra input: plan_only=true

# Live test: dispatch and confirm only the plan job runs in GitHub Actions
erk one-shot "test plan-only flag" --plan-only
# Then check the GitHub Actions run — implement job should be skipped
```

# Plan: Learn trigger should respect draft_pr plan backend

## Context

The `learn.yml` GitHub Actions workflow does NOT accept a `plan_backend` input and does NOT set the `ERK_PLAN_BACKEND` env var. This means when `trigger_async_learn.py` dispatches the workflow, the learn workflow always runs with the default "github" backend — even for draft-PR plans where the plan_id is a PR number.

Compare with `plan-implement.yml` which already handles this correctly:
- Has `plan_backend` input (line 40-43)
- Sets `ERK_PLAN_BACKEND: ${{ inputs.plan_backend }}` (line 101)

For draft-PR plans, this causes the learn workflow to misinterpret the plan_id as an issue number instead of a PR number, and all plan_backend-dependent operations (`find_sessions_for_plan`, `resolve_plan_id_for_branch`, metadata reads) use the wrong backend.

## Changes

### 1. `.github/workflows/learn.yml` — Add plan_backend input

Add `plan_backend` input (matching plan-implement.yml pattern) and set `ERK_PLAN_BACKEND` env var on the job:

```yaml
# Under workflow_dispatch.inputs, add:
plan_backend:
  description: "Plan backend type (github or draft_pr)"
  required: false
  type: string
```

```yaml
# Under jobs.learn.env, add:
ERK_PLAN_BACKEND: ${{ inputs.plan_backend }}
```

### 2. `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — Pass plan_backend when triggering workflow

At line 621-624, the workflow_inputs dict only passes `plan_id` and `gist_url`. Add `plan_backend`:

```python
workflow_inputs: dict[str, str] = {
    "plan_id": plan_id,
    "gist_url": str(gist_url),
    "plan_backend": "draft_pr" if plan_backend.get_provider_name() == "github-draft-pr" else "github",
}
```

The `plan_backend` variable is already available in scope (line 376: `plan_backend = require_plan_backend(ctx)`).

## Files to modify

| File | Change |
|------|--------|
| `.github/workflows/learn.yml` | Add `plan_backend` input + `ERK_PLAN_BACKEND` env var |
| `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` | Pass `plan_backend` in `workflow_inputs` dict (~line 623) |

## Verification

1. Run `make fast-ci` to verify lint/format/types/tests pass
2. Grep for `plan_backend` in learn.yml to confirm input is present
3. Grep for `ERK_PLAN_BACKEND` in learn.yml to confirm env var is set
4. Verify trigger_async_learn.py passes plan_backend in workflow_inputs

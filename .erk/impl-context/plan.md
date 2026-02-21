# Fix: Pass `plan_backend` from one-shot workflow to plan-implement workflow

## Context

One-shot dispatches for draft-PR plans produce empty PRs — the implementation code ends up on a separate branch/PR instead of the plan branch.

**Root cause**: `one-shot.yml` does not pass `plan_backend` to `plan-implement.yml` when calling it as a reusable workflow. The `plan-implement.yml` input defaults to `"github"`, so `ERK_PLAN_BACKEND=github` is set even for draft-PR plans.

This causes `setup_impl_from_issue` to take the issue-based path (`_setup_issue_plan`) instead of the draft-PR path (`_setup_draft_pr_plan`). The issue-based path creates a new `P<N>-...` branch, and Claude implements there, pushing a separate PR. The workflow's post-implementation steps then operate on the original `plan/...` branch which has no code changes.

**Observed failure**: Run #22258386558 — PR #7736 (plan branch) is empty, code landed in PR #7738 (new P-branch).

## Changes

### 1. `src/erk/cli/commands/one_shot_dispatch.py` — Include `plan_backend` in workflow inputs

In the `inputs` dict (around line 328), add the backend type so it's passed to the workflow:

```python
inputs: dict[str, str] = {
    "prompt": truncated_prompt,
    "branch_name": branch_name,
    "pr_number": str(pr_number),
    "submitted_by": submitted_by,
    "plan_backend": "draft_pr" if is_draft_pr else "github",  # NEW
}
```

### 2. `.github/workflows/one-shot.yml` — Accept and forward `plan_backend`

Add `plan_backend` as a workflow input (after `plan_issue_number`, around line 46):

```yaml
plan_backend:
  description: "Plan backend type (github or draft_pr)"
  required: false
  type: string
  default: "github"
```

Pass it through to the implement job's `with:` block (around line 231):

```yaml
plan_backend: ${{ inputs.plan_backend }}
```

## Files Modified

- `src/erk/cli/commands/one_shot_dispatch.py` — add `"plan_backend"` to workflow inputs dict
- `.github/workflows/one-shot.yml` — add input definition + forward to implement job

## Verification

1. Run fast CI to check no tests break
2. Check that the plan job env in `one-shot.yml` doesn't also need `ERK_PLAN_BACKEND` — it currently works without it for planning commands, so no change needed there
3. Manual verification: dispatch a draft-PR one-shot and confirm the implementation lands on the `plan/...` branch (same PR), not a new P-branch

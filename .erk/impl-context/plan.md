# Apply `erk-pr` Label to All Erk-Submitted PRs

## Context

The `erk-pr` label is applied to plan PRs but NOT to non-plan code PRs submitted through erk. This means code PRs like #8992 don't appear in the dash. The fix is simple: apply `erk-pr` to code PRs too via the submit pipeline, and make the dash's "Planned PRs" view query `erk-pr` (showing all erk PRs — both plans and code PRs).

## Changes

### 1. Apply `erk-pr` to non-plan code PRs in submit pipeline

**`src/erk/cli/commands/pr/submit_pipeline.py`**:

Add a new pipeline step `label_code_pr` after `push_and_create_pr` in both `_push_and_create_pipeline()` and `_submit_pipeline()`:

```python
def label_code_pr(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Add erk-pr label to non-plan code PRs."""
    if state.plan_context is not None:
        return state  # Plan PRs already get erk-pr via plan creation
    if state.pr_number is None:
        return state
    add_labels_resilient(
        ctx.github, time=ctx.time, repo_root=state.repo_root,
        pr_number=state.pr_number, labels=(ERK_PR_LABEL,),
    )
    return state
```

Import `ERK_PR_LABEL` from `erk.cli.constants` (already partially imported in this file).

### 2. Rename "Planned PRs" to "PRs" in dash and query `erk-pr`

**`src/erk/tui/views/types.py`** — Change PLANS_VIEW to query `erk-pr` instead of `erk-plan`:

```python
PLANS_VIEW = ViewConfig(
    mode=ViewMode.PLANS,
    display_name="PRs",
    labels=("erk-pr",),
    key_hint="1",
    exclude_labels=("erk-learn",),
)
```

**`src/erk/tui/app.py`** (~line 162) — Remove the "Planned PRs" override in `_display_name_for_view` since `display_name` is now "PRs" directly.

### 3. Update `dash_data.py` default labels

**`src/erk/cli/commands/exec/scripts/dash_data.py`** (~line 50): Change default from `("erk-pr", "erk-plan")` to `("erk-pr",)`.

### 4. Update `pr list` default labels

**`src/erk/cli/commands/pr/list_cmd.py`** (~lines 272, 384): Change default from `("erk-pr", "erk-plan")` to `("erk-pr",)`.

### 5. Update label scheme documentation

**`docs/learned/planning/label-scheme.md`**: Update to reflect that `erk-pr` is the base label on ALL erk-submitted PRs (plans + code).

## Verification

1. `make fast-ci` — all tests pass
2. `erk pr submit` on a non-plan branch → verify PR gets `erk-pr` label
3. `erk dash -i` → tab 1 shows "PRs" (not "Planned PRs"), includes both plan and code PRs

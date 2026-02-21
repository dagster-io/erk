# Objective Update Missing After Land — Diagnosis and Fix

## Context

When PR #7756 was landed via `erk land`, the objective #7709 was not updated afterward. The `land.sh` script that was generated had no `erk exec objective-update-after-land` command — meaning `objective_number` was `None` at script generation time.

The root cause is that the draft-PR plan backend extracts `objective_id` from the PR body's `plan-header` metadata block, but PR #7756's body had no `plan-header` block. The body was a standard implementation PR format (created by remote execution via CI), which replaced the original plan-header during implementation. So when `get_objective_for_branch` asked the plan backend for the plan's objective_id, it got `None`, and the objective update was silently skipped (fail-open design).

The branch name `plan/O7709-plan-lazy-tip-sync-f-02-21-1116` clearly encodes the objective (O7709), but this is never used as a fallback — the code only looks at the plan backend, not the branch name.

## Call Chain

```
land_pipeline.py:resolve_objective
  → objective_helpers.py:get_objective_for_branch
    → draft_pr.py:DraftPRPlanBackend.get_plan_for_branch   (finds PR by branch name, state=all)
      → conversion.py:pr_details_to_plan
        → find_metadata_block(pr.body, "plan-header")      (returns None — no block in body)
        → objective_id = None
    → returns Plan(objective_id=None)
  → returns None
→ render_land_execution_script(objective_number=None)
→ objective_line = ""     ← no objective update emitted
```

## Immediate Workaround

Run this manually to update objective #7709 now:

```bash
erk exec objective-update-after-land --objective 7709 --pr 7756 --branch plan/O7709-plan-lazy-tip-sync-f-02-21-1116
```

## Fix

Two changes are needed:

### 1. Update `extract_objective_number` to handle old `plan/` prefix

File: `packages/erk-shared/src/erk_shared/naming.py:424`

Current regex only handles `planned/` (new prefix after #7749) and `P{number}-O{number}-` (issue-based):

```python
match = re.match(r"^(?:[Pp]?\d+-|planned/)[Oo](\d+)-", branch_name)
```

Update to also handle the old `plan/` prefix:

```python
match = re.match(r"^(?:[Pp]?\d+-|plan(?:ned)?/)[Oo](\d+)-", branch_name)
```

Update the docstring examples to include `plan/O456-fix-auth-01-15-1430` → 456.

### 2. Add branch-name fallback in `get_objective_for_branch`

File: `src/erk/cli/commands/objective_helpers.py:137`

When the plan backend returns a plan but `objective_id` is None (because the PR body lacked the `plan-header` block), fall back to parsing the branch name:

```python
def get_objective_for_branch(ctx: ErkContext, repo_root: Path, branch: str) -> int | None:
    try:
        result = ctx.plan_backend.get_plan_for_branch(repo_root, branch)
    except RuntimeError:
        return extract_objective_number(branch)
    if isinstance(result, PlanNotFound):
        return extract_objective_number(branch)
    if result.objective_id is not None:
        return result.objective_id
    return extract_objective_number(branch)
```

Add `from erk_shared.naming import extract_objective_number` to the imports.

## Files to Modify

- `packages/erk-shared/src/erk_shared/naming.py` — regex update + docstring
- `src/erk/cli/commands/objective_helpers.py` — fallback to branch-name extraction
- `tests/` — update unit tests for `extract_objective_number` and `get_objective_for_branch`

## Verification

1. Run the immediate workaround above and verify objective #7709 gets updated
2. After implementing the fix, write a unit test: when `get_plan_for_branch` returns a `Plan` with `objective_id=None` but the branch is `plan/O7709-some-slug`, `get_objective_for_branch` returns `7709`
3. Verify `extract_objective_number("plan/O456-fix-auth-01-15-1430")` → `456`
4. Verify `extract_objective_number("planned/O456-fix-auth-01-15-1430")` → `456` (unchanged)

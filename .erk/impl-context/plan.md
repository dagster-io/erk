# Fix: Learn PRs closed immediately due to ephemeral base branch

## Context

The learn workflow (`learn.yml`) checks out ephemeral `learn/XXXX` branches, runs `/erk:learn` which calls `plan-save`. The `plan-save` logic in `plan_save.py:185` treats any non-trunk branch as a feature branch and uses it as the PR base ref. The workflow's cleanup step then deletes the `learn/XXXX` branch (`git push origin --delete`), and GitHub auto-closes all PRs whose base was that deleted branch.

**Result:** Every learn plan PR is created and immediately closed without merging. All recent learn PRs (#8174, #8172, #8166, #8158, #8151, etc.) have `mergedAt: null`.

## Fix

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py` (line 185)

Add a check to exclude `learn/` prefixed branches from being used as a PR base, so they fall through to the trunk code path:

```python
is_ephemeral_branch = current_branch is not None and current_branch.startswith("learn/")
if current_branch is not None and current_branch != trunk and not is_ephemeral_branch:
```

This is the minimal correct fix because:
- `learn/` branches are ephemeral by design (deleted by the workflow cleanup step)
- The dispatch step (`dispatch_cmd.py:59-80`) already has separate logic (`get_learn_plan_parent_branch`) for stacking learn implementation PRs on parent branches
- No new CLI flags or workflow changes needed

## Test

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

Add one test: `test_planned_pr_learn_branch_uses_trunk_as_base` — configures `FakeGit` with `current_branch="learn/8163"` and asserts the PR base is `"master"` (trunk), not `"learn/8163"`.

## Verification

1. Run `uv run pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py -v` — all tests pass including the new one
2. Existing `test_planned_pr_feature_branch_creates_correct_pr_base` still passes (feature branch stacking unaffected)

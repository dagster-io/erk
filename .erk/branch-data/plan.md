# Plan: Add `planned/` prefix to plan-originated PR titles

## Context

PRs created through the erk planning process (both remote submission and local implementation) are currently indistinguishable from manually-created PRs by title alone. Adding a `planned/` prefix to these PR titles makes them immediately identifiable in GitHub PR lists.

## Scope

Add the `planned/` prefix to PR titles in **all code paths** that create or finalize plan-linked PRs:

1. `erk plan submit` (remote implementation draft PRs)
2. `erk pr submit` (local implementation PR finalization)
3. `/erk:git-pr-push` (git-only PR creation from plan worktrees)

## Changes

### 1. Add constant — `src/erk/cli/constants.py`

Add `PLANNED_PR_TITLE_PREFIX = "planned/"` alongside existing prefix constants.

### 2. Add helper function — `src/erk/cli/commands/submit.py`

Create `_add_planned_prefix(title: str) -> str` that prepends `planned/` (idempotent — skips if already prefixed). Apply at both PR title sites:

- **Line 493**: `pr_title = _add_planned_prefix(_strip_plan_markers(issue.title))`
- **Line 627**: same pattern in the branch-exists-but-no-PR path

### 3. Add prefix in PR submit pipeline — `src/erk/cli/commands/pr/submit_pipeline.py`

In `finalize_pr()` (~line 617), when the PR is plan-linked (`issue_number is not None`), prepend the prefix to the AI-generated title:

```python
pr_title = state.title or "Update"
if state.issue_number is not None:
    pr_title = _add_planned_prefix(pr_title)
```

Import the constant and helper from `erk.cli.constants`. The commit message amend on line 668 will naturally pick up the prefixed title.

### 4. Update `/erk:git-pr-push` command — `.claude/commands/erk/git-pr-push.md`

Add a step between Step 3 (analyze diff) and Step 4 (create commit) that checks for `.impl/` and prepends `planned/` to the PR title:

```bash
if [ -d ".impl" ]; then
    pr_title="planned/${pr_title}"
fi
```

### 5. Update tests — `tests/commands/submit/test_pr_creation.py`

- Update `test_strip_plan_markers_from_pr_title`: assert title is `"planned/Implement feature X"` instead of `"Implement feature X"`
- Add `test_planned_prefix_idempotent`: verify double-application doesn't double-prefix
- Add `test_planned_prefix_added_to_pr_title`: explicit test for the prefix behavior

## Files to modify

| File | Change |
|------|--------|
| `src/erk/cli/constants.py` | Add `PLANNED_PR_TITLE_PREFIX` |
| `src/erk/cli/commands/submit.py` | Add `_add_planned_prefix()`, apply at lines 493, 627 |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Add prefix in `finalize_pr()` when plan-linked |
| `.claude/commands/erk/git-pr-push.md` | Add `.impl/` check for prefix |
| `tests/commands/submit/test_pr_creation.py` | Update existing + add new tests |

## Verification

1. Run existing submit tests: `pytest tests/commands/submit/`
2. Run submit pipeline tests: `pytest tests/commands/pr/`
3. Verify the prefix appears in PR titles by tracing through both code paths

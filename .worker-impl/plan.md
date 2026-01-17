# Plan: Add `erk exec get-pr-for-plan` Command

## Summary

Create a new exec script that fetches PR details for a plan issue by extracting the branch name from plan metadata and using `get_pr_for_branch`.

## Background

The `/erk:learn` command was incorrectly using `gh pr list --search "head:P5103-"` which is invalid GitHub search syntax. The correct approach is `gh pr list --head <branch-name>`. This command encapsulates the correct pattern.

## Implementation

### New File: `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`

```python
"""Get PR details for a plan issue.

Usage:
    erk exec get-pr-for-plan <issue-number>

Extracts branch_name from plan metadata, then fetches PR for that branch.

Output:
    JSON with PR details or error if not found.
"""
```

**Logic:**
1. Accept `issue_number` argument
2. Fetch issue via `require_github_issues(ctx).get_issue(repo_root, issue_number)`
3. Extract `plan-header` metadata block
4. Get `branch_name` field from metadata
5. Use `require_github(ctx).get_pr_for_branch(repo_root, branch_name)` to get PR
6. Return JSON with PR details

**Response dataclasses:**
- `GetPrForPlanSuccess` - success with PR details (number, title, state, url, head_ref_name, base_ref_name)
- `GetPrForPlanError` - error with type and message

**Error cases:**
- `plan-not-found`: Issue doesn't exist
- `no-branch-in-plan`: Plan metadata missing `branch_name`
- `no-pr-for-branch`: No PR exists for the branch (sentinel `PRNotFound`)

### New File: `tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py`

Tests using `FakeGitHub` and `FakeGitHubIssues`:
1. `test_get_pr_for_plan_success` - PR found for plan branch
2. `test_get_pr_for_plan_no_branch_in_metadata` - Plan exists but no branch_name
3. `test_get_pr_for_plan_no_pr_for_branch` - Branch exists but no PR
4. `test_get_pr_for_plan_issue_not_found` - Plan issue doesn't exist

## Files to Modify/Create

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` | Create |
| `tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py` | Create |

## Verification

1. Run unit tests:
   ```bash
   uv run pytest tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py -v
   ```

2. Run ty/ruff on new files:
   ```bash
   uv run ty check src/erk/cli/commands/exec/scripts/get_pr_for_plan.py
   uv run ruff check src/erk/cli/commands/exec/scripts/get_pr_for_plan.py
   ```

3. Manual test with real plan:
   ```bash
   erk exec get-pr-for-plan 5103
   # Should return: {"success": true, "pr": {"number": 5104, ...}}
   ```

## Skills to Load

- `dignified-python` - for Python coding standards
- `fake-driven-testing` - for test patterns
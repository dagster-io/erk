# Plan: Objective #7911 Nodes 3.3 + 3.4 Cleanup

Part of Objective #7911, Nodes 3.3 and 3.4

## Context

Objective #7911 ("Delete Issue-Based Plan Backend") has been systematically removing issue-based plan infrastructure. Investigating nodes 3.3 and 3.4 reveals that prior PRs (#8210, #8229, #8254) already completed most of the work:

- **Node 3.3**: `plan_migrate_to_draft_pr.py` exec script already deleted, zero references remain
- **Node 3.4**: Dead tests (`test_github_plan_store.py`, `test_plan_migrate_to_draft_pr.py`) already deleted; issue-based submit code already eliminated

The remaining item from 3.4 — `issue_info_to_plan` — **cannot be deleted** because it's actively used for converting objective issues (which are GitHub Issues, not PRs) to Plan objects. However, the function name is misleading now that "issue-based plans" have been eliminated. Additionally, `fetch_plans_by_ids` in the plan data provider uses issue-based fetching for PR-backed plans, which works via GitHub's `issueOrPullRequest` GraphQL but is semantically wrong.

## Goal

Complete dead code elimination for nodes 3.3 + 3.4 by cleaning up the remaining issue-plan naming confusion and marking both nodes as done.

## Implementation

### Phase 1: Rename `issue_info_to_plan` to clarify purpose

The function converts GitHub Issues (specifically objectives) to Plan objects. Rename to make this explicit.

**Files to modify:**

1. `packages/erk-shared/src/erk_shared/plan_store/conversion.py`
   - Rename `issue_info_to_plan` → `github_issue_to_plan`
   - Update docstring to clarify this is for objective issues, not plan issues

2. `src/erk/core/services/objective_list_service.py` (line 22, 59)
   - Update import and usage

3. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (line 66, 450)
   - Update import and usage

4. `tests/unit/plan_store/test_conversion.py` (line 17, class at line 46-102)
   - Update import and all test references

5. `docs/learned/architecture/plan-backend-migration.md` (lines 72, 84)
   - Update references in documentation

### Phase 2: Clarify `fetch_plans_by_ids` intent

The `fetch_plans_by_ids` method in `plan_data_provider/real.py` fetches roadmap-referenced PR numbers through `get_issues_by_numbers_with_pr_linkages`. This works because the GraphQL uses `issueOrPullRequest` which handles both types. The method docstring says "Fetch specific plans by their issue numbers" which is outdated.

**Files to modify:**

1. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (line 429-472)
   - Update method docstring: clarify it fetches plans by number (could be issue or PR)
   - Update parameter name in docstring from "issue numbers" to "plan numbers"

2. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` (line 127-136)
   - Update abstract method docstring to match

### Phase 3: Mark objective nodes as done

```bash
erk exec update-objective-node 7911 --node 3.3 --status done
erk exec update-objective-node 7911 --node 3.4 --status done --pr <this-pr-number>
```

Post an action comment on the objective summarizing what was done.

## Verification

1. Run unit tests for modified files:
   - `tests/unit/plan_store/test_conversion.py`
   - `tests/tui/data/test_provider.py`
   - `tests/tui/screens/test_objective_plans_screen.py`
2. Run ty type checker on modified packages
3. Run ruff linter
4. Grep for any remaining references to `issue_info_to_plan` to confirm clean rename

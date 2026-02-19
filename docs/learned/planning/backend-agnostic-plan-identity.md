---
title: Backend-Agnostic Plan Identity
read_when:
  - "working with PlanBackend or plan resolution"
  - "adding a new plan storage backend"
  - "typing plan identifiers in function signatures"
  - "extracting metadata from plan issue bodies"
tripwires:
  - action: "manually extracting metadata from plan issue body instead of using Plan.objective_id"
    warning: "Use pre-parsed Plan fields. Plan.objective_id is extracted during conversion. Manual regex/YAML parsing is error-prone."
  - action: "typing plan identifiers as just int"
    warning: "Plan identifiers must be str | int to accommodate both issue-based and draft-PR-based plans."
last_audited: "2026-02-19 00:00 PT"
audit_result: clean
---

# Backend-Agnostic Plan Identity

Plan resolution was originally hardcoded to GitHub issues. Draft PR plans need the same resolution without issue numbers. The `PlanBackend` ABC abstracts over both storage mechanisms.

## Two Backend Implementations

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/backend.py, PlanBackend -->

`PlanBackend` (in `packages/erk-shared/src/erk_shared/plan_store/backend.py`) defines `get_plan_for_branch()` returning `Plan | PlanNotFound` (discriminated union).

| Backend       | Class                | Resolution Strategy                         |
| ------------- | -------------------- | ------------------------------------------- |
| GitHub Issues | `GitHubPlanStore`    | Regex-based branch name parsing (zero-cost) |
| Draft PRs     | `DraftPRPlanBackend` | API-based via `github.get_pr_for_branch()`  |

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore -->
<!-- Source: packages/erk-shared/src/erk_shared/plan_store/draft_pr.py, DraftPRPlanBackend -->

`GitHubPlanStore` extracts the issue number from the branch name using regex (e.g., `P123-fix-bug-01-15-1430` → issue 123). This is zero-cost — no API call needed.

`DraftPRPlanBackend` calls `github.get_pr_for_branch()` to find the PR associated with the branch, then reads the plan from the PR body or committed files.

## Pre-Parsed Plan Metadata

Plans carry pre-parsed metadata fields to avoid repeated YAML parsing by callers:

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/conversion.py -->

| Field           | Type                | Source                                  |
| --------------- | ------------------- | --------------------------------------- |
| `header_fields` | `dict[str, object]` | Full parsed header block                |
| `objective_id`  | `int \| None`       | Extracted from `objective_issue` header |

Typed accessors for `header_fields`: `header_str()`, `header_int()`, `header_datetime()`.

See `issue_info_to_plan()` and `pr_details_to_plan()` in `packages/erk-shared/src/erk_shared/plan_store/conversion.py` for the single-parse conversions that populate these fields.

## Plan Identifier Typing

`PlanInfoDict.number` is typed as `str | int` to accommodate both backends — issue numbers are `int`, draft PR identifiers are `str`.

<!-- Source: packages/erk-shared/src/erk_shared/objective_fetch_context_result.py, PlanInfoDict -->

See `PlanInfoDict` in `packages/erk-shared/src/erk_shared/objective_fetch_context_result.py` for the full TypedDict definition.

When writing code that handles plan identifiers, always use `str | int`, not bare `int`.

## Exec Script Migration: `--issue-number` → `--plan-id`

CI workflows and exec scripts migrated from `--issue-number` to `--plan-id` to support both backends:

**Migrated scripts:**

- `ci_update_pr_body.py`
- `handle_no_changes.py`
- `post_workflow_started_comment.py`
- `upload_session.py`
- `update_plan_remote_session.py`

**Not yet migrated (still uses `--issue-number`):**

- `register_one_shot_plan.py`
- `get_pr_body_footer.py`
- `plan_update_issue.py`

## Related Topics

- [Branch Manager Decision Tree](../architecture/branch-manager-decision-tree.md) - Branch creation for plan branches
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - `Plan | PlanNotFound` pattern

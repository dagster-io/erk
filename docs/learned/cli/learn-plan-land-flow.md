---
title: Learn Plan Land Flow
read_when:
  - "landing PRs associated with learn plans"
  - "understanding learn plan status transitions"
  - "working with tripwire documentation promotion"
tripwires:
  - action: "landing a PR without updating associated learn plan status"
    warning: "Learn plan PRs trigger special execution pipeline steps: check_learn_status, update_learn_plan, promote_tripwires, close_review_pr. Ensure these steps execute after PR merge."
last_audited: "2026-02-05"
audit_result: edited
---

# Learn Plan Land Flow

Learn plan branches require special handling in the land command execution pipeline. After the PR merges, the land command updates plan status, promotes tripwires to category files, and closes review PRs.

## Learn Plan Detection

Learn plans are detected during the validation pipeline by checking:

- PR has `erk-learn` label, OR
- Branch name starts with `erk-learn-`

Once detected, `state.is_learn_plan = True` triggers learn-specific execution steps.

## Execution Pipeline Steps

<!-- Source: src/erk/cli/commands/land_pipeline.py -->

See `src/erk/cli/commands/land_pipeline.py` for the full execution pipeline implementation. The learn-specific steps are:

1. **merge_pr_step** (standard) — Merges the PR normally
2. **check_learn_status** — Verifies learn plan issue exists, extracts issue number
3. **update_learn_plan** — Updates learn plan issue status to "Landed"
4. **promote_tripwires** — Promotes tripwires from plan to category `tripwires.md` files
5. **close_review_pr** — Closes associated review PR if one exists
6. **cleanup_branches** (standard) — Deletes feature branches

All learn steps skip execution if `state.is_learn_plan == False`.

## State Field Usage

| Field                  | Populated By         | Used By             |
| ---------------------- | -------------------- | ------------------- |
| `is_learn_plan`        | `validate_checks`    | All learn steps     |
| `learn_issue_number`   | `check_learn_status` | `update_learn_plan` |
| `learn_tripwire_files` | `promote_tripwires`  | Logging only        |
| `has_review_pr`        | `validate_checks`    | `close_review_pr`   |

## Error Handling

| Error Type                 | Meaning                         | Recovery                     |
| -------------------------- | ------------------------------- | ---------------------------- |
| `learn-issue-not-found`    | Issue link missing or invalid   | Fix PR body, re-run land     |
| `learn-plan-update-failed` | GitHub API error updating issue | Manually update issue status |
| `review-pr-close-failed`   | GitHub API error closing PR     | Manually close review PR     |

All errors short-circuit the execution pipeline (no further steps run).

## Related Documentation

- [Linear Pipelines](../architecture/linear-pipelines.md) - Two-pipeline pattern overview
- [Land State Threading](../architecture/land-state-threading.md) - State field lifecycle
- [Learn Workflow](../planning/learn-workflow.md) - Learn plan lifecycle

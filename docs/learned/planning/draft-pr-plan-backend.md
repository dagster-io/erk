---
title: Draft PR Plan Backend
read_when:
  - "working with plan storage or plan backends"
  - "adding plan storage behavior without checking plan backend type"
  - "understanding how plans are stored as draft pull requests"
  - "modifying plan-save or land pipeline for plan handling"
tripwires:
  - action: "adding plan storage behavior without checking plan backend type"
    warning: "Two backends exist (github, draft_pr). Verify behavior works for both. See draft-pr-plan-backend.md."
---

# Draft PR Plan Backend

DraftPRPlanBackend stores plans as GitHub draft pull requests instead of issues. It is an alternative to the default GitHubPlanStore (issue-based) backend.

## Backend Selection

Backend selection is controlled by the `ERK_PLAN_BACKEND` environment variable, read by `get_plan_backend()` in `packages/erk-shared/src/erk_shared/plan_store/__init__.py:19-24`:

- `"github"` (default): Issue-based storage via GitHubPlanStore
- `"draft_pr"`: Draft PR-based storage via DraftPRPlanBackend

Context creation in `src/erk/core/context.py:604-609` uses this to select both the plan store and plan list service:

<!-- Source: src/erk/core/context.py, create_context -->

See backend selection in `create_context()` in `src/erk/core/context.py` — dispatches on `get_plan_backend()` to select GitHubPlanStore or DraftPRPlanBackend.

## Architecture

DraftPRPlanBackend uses **composition** — it wraps the top-level GitHub gateway, not inheritance. The class is at `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py`.

Key design decisions:

- **Lightweight init**: No I/O in `__init__`, dependencies injected (`github`, `time`)
- **Provider name**: `"github-draft-pr"` (used for conditional dispatch elsewhere)
- **Immutable metadata fields**: `schema_version`, `created_at`, `created_by` are protected from updates

## PR Body Format

Plan PRs use a structured body format: metadata block + separator + plan content.

- **Separator**: `"\n\n---\n\n"`
- **Label**: `"erk-plan"`
- **Structure**: `<!-- plan-header metadata -->` + separator + `# Plan: Title` + content

Helper functions `build_plan_stage_body()` and `extract_plan_content()` (public, in `draft_pr_lifecycle.py`) handle composition and extraction.

## Plan File Commit

Plans are committed to `.erk/plan/PLAN.md` on the draft PR branch. The `plan_save.py` script uses a try/finally pattern for branch restoration — see [plan-save-branch-restoration.md](../architecture/plan-save-branch-restoration.md).

## Branch Naming

Two branch name formats are supported:

- **P-prefix**: `P{number}-{slug}` (standard plan branches)
- **Objective format**: `P{number}-O{objective}-{slug}` (plans linked to objectives)

See [branch-plan-resolution.md](branch-plan-resolution.md) for how branches resolve to plans.

## Land Pipeline Integration

The `close_review_pr()` function in `src/erk/cli/commands/land_pipeline.py:469-471` skips cleanup for draft-PR plans since they don't have separate review PRs:

<!-- Source: src/erk/cli/commands/land_pipeline.py, close_review_pr -->

See `close_review_pr()` in `src/erk/cli/commands/land_pipeline.py` — skips cleanup for draft-PR plans.

## Type Narrowing

The backend uses explicit `isinstance()` checks and conditional type conversion for metadata fields, following LBYL discipline rather than `cast()`.

## Title Prefixing Behavior

Draft PR titles (and issue-based plan titles) are prefixed with a label-based tag via `get_title_tag_from_labels()` in `packages/erk-shared/src/erk_shared/plan_utils.py:178-190`.

<!-- Source: packages/erk-shared/src/erk_shared/plan_utils.py:178-190, get_title_tag_from_labels -->

The function returns `"[erk-learn]"` if `"erk-learn"` is in the labels list, otherwise `"[erk-plan]"`. The prefix is prepended to the plan title during PR creation (e.g., `[erk-plan] My Feature`). For erk-learn plans, the prefix becomes `[erk-learn]` to distinguish documentation/learning plans from implementation plans in the PR list.

## GraphQL Refactor: `list_plan_prs_with_details()`

The plan data provider fetches PRs via a single GraphQL query (`list_plan_prs_with_details()`) instead of N+1 REST calls. This function lives in `packages/erk-shared/src/erk_shared/gateway/github/real.py:1588` and returns:

- `list[PRDetails]` — for plan content extraction
- `dict[int, list[PullRequestInfo]]` — for display metadata (checks, review threads, merge status)

The single query uses `GET_PLAN_PRS_WITH_DETAILS_QUERY` from `graphql_queries.py` and fetches review decision, conflict status, and CI checks in one round-trip, replacing the previous approach of fetching each PR individually.

## Related Topics

- [Branch Plan Resolution](branch-plan-resolution.md) - How branches resolve to plans
- [Plan Save Branch Restoration](../architecture/plan-save-branch-restoration.md) - Try/finally pattern for branch safety
- [Dual Backend Testing](../testing/dual-backend-testing.md) - Testing across both backends

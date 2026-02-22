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
  - action: "validating plan_id in exec scripts without checking provider type"
    warning: "Draft-PR plan_id IS the PR number (not an issue number). Check provider type before assuming plan_id semantics. Issue-based plans use issue numbers; draft-PR plans use PR numbers."
    score: 4
  - action: "reading ERK_PLAN_BACKEND env var inside inner functions when global_config is already in scope"
    warning: "Backend detection precedence: when GlobalConfig.plan_backend is available via context, use it. Never fall back to re-reading env vars inside inner functions if global_config is already in scope — the context value takes precedence and re-reading env vars bypasses context overrides."
    score: 8
  - action: "spawning a GitHub Actions workflow from erk without passing plan_backend as an explicit input"
    warning: "Draft-PR backend propagation: GitHub Actions reusable workflows (workflow_call) do NOT inherit environment variables from the caller. ERK_PLAN_BACKEND must be declared as an explicit workflow input and passed by the caller. Ambient env vars are invisible to reusable workflows."
    score: 9
  - action: "implementing RealPlanListService or DraftPRPlanListService without checking the other for parity"
    warning: "Both plan list services must handle parameters identically. Interface contracts are not enforced by the type system — behavioral divergence between the two services causes subtle bugs when switching backends."
    score: 6
  - action: "using gh issue view on a plan ID without checking plan backend type"
    warning: "Draft-PR plan IDs are PR numbers. Using gh issue view on a draft-PR plan produces a confusing 404. Route to gh pr view based on backend type."
    score: 7
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

Three branch name formats are supported:

- **P-prefix**: `P{number}-{slug}` (issue-based plan branches)
- **Objective format**: `P{number}-O{objective}-{slug}` (plans linked to objectives)
- **Draft-PR**: `plnd/{slug}-{MM-DD-HHMM}` or `plnd/O{objective}-{slug}-{MM-DD-HHMM}` (draft-PR plans)

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

## Implementation Setup and .erk/impl-context/ Cleanup

When implementing a draft-PR plan, the `.erk/impl-context/` staging directory must be cleaned up before implementation begins. This directory contains `plan.md` and `ref.json` committed during plan-save to give the draft PR a non-empty diff.

**Cleanup pattern:**

1. `setup_impl_from_issue.py` reads the files into `.impl/` but does NOT delete them (deferred cleanup)
2. `plan-implement.md` Step 2d performs the actual `git rm -rf .erk/impl-context/ && git commit && git push`
3. The step is **idempotent** — safe to run when the directory doesn't exist

**Rebase conflict handling:** After cleanup commits on the plan branch, a `git pull --rebase` may be needed before pushing further implementation commits. Skipping this can cause non-fast-forward push failures when the remote branch has diverged.

For full details, see [Impl-Context Staging Directory](impl-context.md).

## Related Topics

- [Branch Plan Resolution](branch-plan-resolution.md) - How branches resolve to plans
- [Plan Save Branch Restoration](../architecture/plan-save-branch-restoration.md) - Try/finally pattern for branch safety
- [Dual Backend Testing](../testing/dual-backend-testing.md) - Testing across both backends
- [Impl-Context Staging Directory](impl-context.md) - Staging directory lifecycle and cleanup

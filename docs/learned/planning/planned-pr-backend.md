---
title: Planned PR Backend
read_when:
  - "working with plan storage or plan backends"
  - "adding plan storage behavior without checking plan backend type"
  - "understanding how plans are stored as planned pull requests"
  - "modifying plan-save or land pipeline for plan handling"
tripwires:
  - action: "validating plan_id in exec scripts without checking provider type"
    warning: "Planned PR plan_id IS the PR number (not an issue number). Check provider type before assuming plan_id semantics. Issue-based plans use issue numbers; planned-PR plans use PR numbers."
    score: 4
  - action: "using gh issue view on a plan ID without checking plan backend type"
    warning: "Planned PR plan IDs are PR numbers. Using gh issue view on a planned-PR plan produces a confusing 404. Route to gh pr view based on backend type."
    score: 7
  - action: "checking erk exec plan-save --format json output for empty result"
    warning: "Empty stdout does not mean failure. The duplicate-detection path writes JSON to stderr, not stdout. Always capture both streams with 2>&1 or check for empty stdout and retry with stderr capture."
    score: 5
---

# Planned PR Backend

PlannedPRBackend stores plans as GitHub draft pull requests. It is the only active plan storage backend.

## Backend Selection

The plan backend is hardcoded to `"planned_pr"`. All plans are stored as GitHub draft pull requests via PlannedPRBackend. The former `get_plan_backend()` function and `PlanBackendType` type alias were deleted in PR #7971 (objective #7911 node 1.1).

The `ERK_PLAN_BACKEND` environment variable is no longer read by application code. Setting it has no effect. CI workflows and test fixtures that reference it are vestigial and will be removed in later nodes of objective #7911.

**Note:** Some code still contains `PLAN_BACKEND_SPLIT` comment blocks marking dead branches (e.g., `if "planned_pr" != "planned_pr":` in plan_save.py). These are intentionally preserved for node 1.2 cleanup.

<!-- Source: src/erk/core/context.py, create_context -->

## Architecture

PlannedPRBackend uses **composition** — it wraps the top-level GitHub gateway, not inheritance. The class is at `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`.

Key design decisions:

- **Lightweight init**: No I/O in `__init__`, dependencies injected (`github`, `time`)
- **Provider name**: `"github-draft-pr"` (used for conditional dispatch elsewhere)
- **Immutable metadata fields**: `schema_version`, `created_at`, `created_by` are protected from updates

## PR Body Format

Plan PRs use a structured body format: metadata block + separator + plan content.

- **Separator**: `"\n\n---\n\n"`
- **Label**: `"erk-plan"`
- **Structure**: `<!-- plan-header metadata -->` + separator + `# Plan: Title` + content

Helper functions `build_plan_stage_body()` and `extract_plan_content()` (public, in `planned_pr_lifecycle.py`) handle composition and extraction.

## Plan File Commit

Plans are committed to `.erk/impl-context/plan.md` on the planned PR branch. The `plan_save.py` script uses `commit_files_to_branch()` — a git plumbing approach that writes directly to the branch without checking it out, avoiding race conditions when multiple sessions share the same worktree.

## Branch Naming

Three branch name formats are supported:

- **P-prefix**: `P{number}-{slug}` (issue-based plan branches)
- **Objective format**: `P{number}-O{objective}-{slug}` (plans linked to objectives)
- **Planned PR**: `plnd/{slug}-{MM-DD-HHMM}` or `plnd/O{objective}-{slug}-{MM-DD-HHMM}` (planned-PR plans)

See [branch-plan-resolution.md](branch-plan-resolution.md) for how branches resolve to plans.

## Land Pipeline Integration

Planned PR plans don't have separate review PRs, so the land pipeline skips review PR cleanup for them.

## Type Narrowing

The backend uses explicit `isinstance()` checks and conditional type conversion for metadata fields, following LBYL discipline rather than `cast()`.

## Title Prefixing Behavior

Planned PR titles (and issue-based plan titles) are prefixed with a label-based tag via `get_title_tag_from_labels()` in `packages/erk-shared/src/erk_shared/plan_utils.py:178-190`.

<!-- Source: packages/erk-shared/src/erk_shared/plan_utils.py:178-190, get_title_tag_from_labels -->

The function returns `"[erk-learn]"` if `"erk-learn"` is in the labels list, otherwise `"[erk-plan]"`. The prefix is prepended to the plan title during PR creation (e.g., `[erk-plan] My Feature`). For erk-learn plans, the prefix becomes `[erk-learn]` to distinguish documentation/learning plans from implementation plans in the PR list.

## GraphQL Refactor: `list_plan_prs_with_details()`

The plan data provider fetches PRs via a single GraphQL query (`list_plan_prs_with_details()`) instead of N+1 REST calls. This function lives in `packages/erk-shared/src/erk_shared/gateway/github/real.py:1636` and returns:

- `list[PRDetails]` — for plan content extraction
- `dict[int, list[PullRequestInfo]]` — for display metadata (checks, review threads, merge status)

The single query uses `GET_PLAN_PRS_WITH_DETAILS_QUERY` from `graphql_queries.py` and fetches review decision, conflict status, and CI checks in one round-trip, replacing the previous approach of fetching each PR individually.

## Implementation Setup and .erk/impl-context/ Cleanup

When implementing a planned-PR plan, the `.erk/impl-context/` staging directory must be cleaned up before implementation begins. This directory contains `plan.md` and `ref.json` committed during plan-save to give the draft PR a non-empty diff.

**Cleanup pattern:**

1. `setup_impl_from_issue.py` reads the files into `.impl/` but does NOT delete them (deferred cleanup)
2. `plan-implement.md` Step 2d performs the actual `git rm -rf .erk/impl-context/ && git commit && git push`
3. The step is **idempotent** — safe to run when the directory doesn't exist

**Rebase conflict handling:** After cleanup commits on the plan branch, a `git pull --rebase` may be needed before pushing further implementation commits. Skipping this can cause non-fast-forward push failures when the remote branch has diverged.

For full details, see [Impl-Context Staging Directory](impl-context.md).

## plan-save Duplicate Detection Output Routing

When `erk exec plan-save --format json` detects that a plan was already saved in the current session (via the `plan-saved-issue` marker), it returns `{"skipped_duplicate": true, "plan_number": <N>}`. This JSON is written to **stderr**, not stdout.

Empty stdout from `plan-save` does not indicate failure. Always capture both streams:

```bash
erk exec plan-save --format json --session-id "..." 2>&1
```

If stdout is empty, check stderr for the duplicate-detection response before assuming the command failed.

## Related Topics

- [Branch Plan Resolution](branch-plan-resolution.md) - How branches resolve to plans
- [Plan Save Branch Restoration](../architecture/plan-save-branch-restoration.md) - Git plumbing approach for branch safety
- [Plan Storage Testing](../testing/dual-backend-testing.md) - Plan storage testing patterns
- [Impl-Context Staging Directory](impl-context.md) - Staging directory lifecycle and cleanup

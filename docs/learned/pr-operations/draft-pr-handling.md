---
title: Draft PR Handling
read_when:
  - creating or working with draft PRs
  - understanding when to use draft status
  - converting between draft and ready for review
  - debugging why CI didn't run on a PR
  - working with orphaned or duplicate PRs for a plan
tripwires:
  - action: "creating a PR without draft=True in automated workflows"
    warning: "All automated erk PR creation uses draft mode. This gates CI costs and prevents premature review. See draft-pr-handling.md."
  - action: "using gh pr ready instead of the gateway's mark_pr_ready method"
    warning: "mark_pr_ready uses REST API to preserve GraphQL quota. Don't shell out to gh pr ready directly."
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
---

# Draft PR Handling

Erk uses draft PRs as a **CI cost gate and review coordination mechanism**, not just a work-in-progress signal. Every automated PR creation in erk passes `draft=True` — this is a deliberate architectural choice that connects PR creation, CI workflows, and orphan cleanup into a unified lifecycle.

## Why Draft-First Matters

Draft status controls two expensive systems:

1. **CI execution** — Every job in `ci.yml` and every code review in `code-reviews.yml` gates on `github.event.pull_request.draft != true`. Creating PRs as drafts means zero CI cost until the work is explicitly marked ready.

2. **Code reviews** — The `code-reviews.yml` workflow (convention-based review discovery) also skips draft PRs. This prevents review agents from analyzing incomplete work.

The CI workflow listens for the `ready_for_review` event type (alongside `opened`, `synchronize`, `reopened`), so transitioning a PR from draft to ready automatically triggers the full CI suite without requiring a new push.

## The Draft→Ready Lifecycle

Draft PRs in erk follow a lifecycle that spans multiple systems:

| Phase          | System                                 | What happens                               |
| -------------- | -------------------------------------- | ------------------------------------------ |
| **Create**     | `erk submit` / `plan-create-review-pr` | PR created with `draft=True` via gateway   |
| **Implement**  | GitHub Actions workflow                | Agent works on the draft PR branch         |
| **Transition** | `handle-no-changes` / manual           | `mark_pr_ready()` called via REST API      |
| **CI runs**    | `ci.yml`, `code-reviews.yml`           | `ready_for_review` event triggers all jobs |

<!-- Source: src/erk/cli/commands/submit.py, _create_branch_and_pr -->

The submit command creates draft PRs for plan implementation. The `handle-no-changes` exec script marks PRs ready when implementation produces no code changes (duplicate plan, work already merged), converting the draft into an informational PR that users can review and close.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/abc.py, GitHubGateway.mark_pr_ready -->

**REST vs GraphQL for mark_pr_ready**: The gateway uses `gh api --method PATCH` (REST) rather than `gh pr ready` (GraphQL) to preserve GraphQL quota. This is documented in the real gateway implementation with the `GH-API-AUDIT` comment pattern.

## Orphaned Draft Cleanup

When a plan is re-submitted, old draft PRs become orphans. Erk automatically cleans these up:

<!-- Source: src/erk/cli/commands/submit.py, _close_orphaned_draft_prs -->

After creating a new draft PR for a plan issue, `_close_orphaned_draft_prs()` finds all other open draft PRs linked to the same issue number and closes them. The criteria are specific: only PRs that are both **draft** and **OPEN** (and not the just-created PR) get closed. Non-draft PRs are left alone — this prevents accidentally closing a PR that was manually marked ready and is under active review.

This cleanup runs in both the direct-submit and dispatch-submit code paths.

## Draft PRs in Stacked Workflows (Graphite)

When using Graphite for stacked PRs, draft status does **not** cascade:

- `gt submit --draft` creates all PRs in the stack as draft
- Marking a base PR ready does not auto-mark dependent PRs ready (GitHub limitation)
- After base merges, dependent PRs must be individually marked ready with `gh pr ready` or via the gateway

## Related Documentation

- [PR Submission Workflow](pr-submission-workflow.md) — Git-only PR creation path
- [PR Creation Decision Logic](pr-creation-patterns.md) — Check-before-create pattern for avoiding duplicates

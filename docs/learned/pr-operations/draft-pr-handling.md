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

## Auto-Publishing in `finalize_pr()`

After code submission, `finalize_pr()` in `src/erk/cli/commands/pr/submit_pipeline.py:687-691` automatically publishes draft PRs.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py:687-691, finalize_pr -->

This runs as part of the `erk pr submit` pipeline. The function:

1. Fetches the current PR state to verify it's still a draft
2. If draft, calls `mark_pr_ready()` via the gateway (REST API)
3. Echoes a "Publishing draft PR..." feedback message to the user

This is the mechanism by which draft-PR-backed plans get published for review after `erk pr submit` finishes. The draft status is used during planning/implementation to suppress CI, then auto-removed on submit.

## Draft PRs in Stacked Workflows (Graphite)

When using Graphite for stacked PRs, draft status does **not** cascade:

- `gt submit --draft` creates all PRs in the stack as draft
- Marking a base PR ready does not auto-mark dependent PRs ready (GitHub limitation)
- After base merges, dependent PRs must be individually marked ready with `gh pr ready` or via the gateway

## Troubleshooting: Common Failures

### Non-Fast-Forward Push

**Cause**: Missing `pull_rebase()` in the submit path for draft-PR plans. The local branch was behind remote after checkout.

**Symptoms**: `git push` fails with "non-fast-forward" error during `erk pr submit`.

**Resolution**: Fixed in PR #7697 by adding `pull_rebase()` to the submit path's three-step sync sequence. See [Draft PR Branch Sync](../planning/draft-pr-branch-sync.md#pattern-consistency-setup-and-submit).

### Graphite Divergence

**Cause**: Branch updated remotely (by CI or another session) between local changes and `gt submit`.

**Symptoms**: `gt submit` fails or `erk pr submit` returns `remote_diverged` error with behind count.

**Resolution**: Run `erk pr sync-divergence --dangerous` to fetch, rebase, and resolve conflicts. Or use `erk pr submit -f` to force push (overrides remote). See [Graphite Divergence Detection](../erk/graphite-divergence-detection.md).

### .erk/impl-context/ Already Exists

**Cause**: Stale `.erk/impl-context/` from a prior failed submission was not cleaned up.

**Symptoms**: `create_impl_context()` fails because the directory already exists.

**Resolution**: Fixed in PR #7687 by adding LBYL cleanup: `if impl_context_exists(): remove_impl_context()` before creation in both submit paths.

### Footer Separator False Match

**Cause**: Accidental `\n\n---\n\n` formed from "Remotely executed" notes ending with a blank line followed by the footer delimiter.

**Symptoms**: `extract_metadata_prefix()` or `extract_plan_content()` returns incorrect content, causing plan body corruption during stage transitions.

**Resolution**: `extract_metadata_prefix()` validates the `<!-- erk:metadata-block:` marker in the prefix. See [Draft PR Lifecycle — False Match Prevention](../planning/draft-pr-lifecycle.md#false-match-prevention).

## Related Documentation

- [PR Submission Workflow](pr-submission-workflow.md) — Git-only PR creation path
- [PR Creation Decision Logic](pr-creation-patterns.md) — Check-before-create pattern for avoiding duplicates

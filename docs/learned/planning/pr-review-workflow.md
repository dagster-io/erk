---
title: PR-Based Plan Review Workflow
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
read_when:
  - creating or managing plan review PRs
  - addressing feedback on plan content via PR comments
  - understanding how review PRs relate to implementation PRs
  - closing or cleaning up plan review PRs
tripwires:
  - action: "merging a plan review PR"
    warning: "Plan review PRs are NEVER merged. They exist only for inline review comments. Close without merging when review is complete."
  - action: "blocking implementation on review PR feedback"
    warning: "Review PRs are advisory and non-blocking. Implementation can proceed regardless of review PR state."
  - action: "editing plan content only in the PR branch without syncing"
    warning: "Plan content lives in two places (PR branch + issue comment). Edit the local file, then sync to the issue with `erk exec plan-update-from-feedback`. See plan-file-sync-pattern.md."
---

# PR-Based Plan Review Workflow

Plan review PRs are ephemeral PRs that exist solely to enable GitHub's inline review UI on plan content. They are never merged — the plan issue remains the canonical source of truth, and the review PR is discarded after feedback is incorporated.

## Why Ephemeral PRs Instead of Issue Comments

GitHub Issues lack inline review — reviewers can only comment on the whole document. By placing plan content in a PR as a markdown file (`PLAN-REVIEW-{issue}.md`), reviewers get line-level commenting, suggestion blocks, and threaded discussions. The trade-off is maintaining two copies of the plan content (PR branch + issue comment), which requires explicit sync.

## The Three-Script Pipeline

The review workflow is split across three exec scripts, each handling one phase of the lifecycle. This separation exists because each phase has distinct failure modes and the `/erk:plan-review` command orchestrates them sequentially with error handling between steps.

<!-- Source: src/erk/cli/commands/exec/scripts/plan_submit_for_review.py, plan_submit_for_review -->
<!-- Source: src/erk/cli/commands/exec/scripts/plan_create_review_branch.py, plan_create_review_branch -->
<!-- Source: src/erk/cli/commands/exec/scripts/plan_create_review_pr.py, plan_create_review_pr -->

| Phase   | Script                      | What It Does                                                 | Key Side Effect                       |
| ------- | --------------------------- | ------------------------------------------------------------ | ------------------------------------- |
| Extract | `plan-submit-for-review`    | Validates issue and extracts plan content                    | None (read-only)                      |
| Branch  | `plan-create-review-branch` | Creates timestamped branch from origin/master with plan file | Git branch + push                     |
| PR      | `plan-create-review-pr`     | Creates draft PR and updates plan-header metadata            | PR created + `review_pr` metadata set |

The extract phase is the oldest script and predates the branch+PR split. In current usage, `/erk:plan-review` skips it and calls the branch and PR scripts directly, since they perform their own validation internally.

## Metadata Linkage: review_pr and last_review_pr

The plan-header metadata block tracks review PR state through two fields that follow the archive-on-clear pattern:

- **`review_pr`**: Active review PR number (set on creation, cleared on completion)
- **`last_review_pr`**: Archived value from previous review (set when `review_pr` is cleared)

This metadata enables two key behaviors:

1. **Idempotency**: The `/erk:plan-review` command checks `review_pr` before creating a new one, preventing duplicate review PRs
2. **Re-review detection**: If `last_review_pr` is set, the command warns that a previous review existed and asks for confirmation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py, clear_plan_header_review_pr -->

See `clear_plan_header_review_pr()` in `plan_header.py` for the archive-on-clear implementation. See [Archive-on-Clear Metadata Pattern](../architecture/metadata-archival-pattern.md) for the general pattern.

## Dual Storage and the Sync Requirement

Plan content exists in two locations during review:

| Location                              | Updated by                           | Purpose                           |
| ------------------------------------- | ------------------------------------ | --------------------------------- |
| `PLAN-REVIEW-{issue}.md` in PR branch | Git commit + push                    | Inline review UI                  |
| Issue comment (plan-body block)       | `erk exec plan-update-from-feedback` | Canonical plan for implementation |

Changes to the local file do NOT automatically propagate to the issue. Agents must explicitly sync after incorporating feedback. Without sync, the implementation pipeline reads stale plan content from the issue while reviewers see updated content in the PR.

See [Plan File Sync Pattern](../architecture/plan-file-sync-pattern.md) for the sync mechanics and decision framework.

## Non-Blocking Relationship with Implementation

Review PRs are **advisory, not gating**. Implementation can proceed at any time regardless of review state. This is a deliberate design choice: review provides asynchronous feedback but should never block forward progress. The plan itself is the source of truth; review feedback is incorporated at the author's discretion.

This means a plan can have both an active review PR and an active implementation PR simultaneously. They don't interfere because they target different branches.

## Cleanup: Three Trigger Points

Review PRs are cleaned up (closed without merging + branch deleted + metadata archived) through three paths:

| Trigger                 | Command                                    | Behavior                                           |
| ----------------------- | ------------------------------------------ | -------------------------------------------------- |
| Explicit completion     | `erk exec plan-review-complete`            | Full cleanup with metadata archival                |
| Plan landed (PR merged) | `cleanup_review_pr()` via `erk land`       | Fail-open — landing succeeds even if cleanup fails |
| Plan closed             | `cleanup_review_pr()` via `erk plan close` | Fail-open — closing succeeds even if cleanup fails |

<!-- Source: src/erk/cli/commands/review_pr_cleanup.py, cleanup_review_pr -->
<!-- Source: src/erk/cli/commands/exec/scripts/plan_review_complete.py, _plan_review_complete_impl -->

The `cleanup_review_pr()` shared helper uses fail-open semantics: if the review PR close or metadata update fails, the main operation (land or close) still succeeds with a warning. This prevents orphaned review PRs from blocking critical operations.

`plan-review-complete` provides the explicit path with full status reporting, while `cleanup_review_pr()` is the implicit path that fires as a side effect of landing or closing.

## Label-Based Workflow Detection

Review PRs receive the `erk-plan-review` label automatically during creation. This label serves as a workflow router: when `/erk:pr-address` runs against a PR with this label, it activates Plan Review Mode instead of Code Review Mode. In Plan Review Mode, feedback is applied to the plan markdown file rather than source code, and the sync step is added to the workflow.

## Anti-Patterns

**Merging a review PR**: Review PRs contain a single markdown file, not code. Merging would add a `PLAN-REVIEW-{issue}.md` file to the repository permanently. Always close without merging.

**Editing the issue comment directly**: Changes to the issue comment won't appear in the PR diff, so reviewers won't see them. Always edit the local file and sync.

**Creating review PRs for simple plans**: The overhead of dual storage and sync is only worthwhile when the plan genuinely needs collaborative feedback. For routine plans, skip directly to implementation.

## Related Documentation

- [Plan File Sync Pattern](../architecture/plan-file-sync-pattern.md) — Dual storage sync mechanics
- [Archive-on-Clear Metadata Pattern](../architecture/metadata-archival-pattern.md) — review_pr/last_review_pr lifecycle
- [Plan Lifecycle](lifecycle.md) — Phase 2b covers review in the broader lifecycle context
- [Planning Workflow](workflow.md) — Option E covers review in the exit-plan-mode decision tree
- [PR Address Workflows](../erk/pr-address-workflows.md) — Plan Review Mode vs Code Review Mode

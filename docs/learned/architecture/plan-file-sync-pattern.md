---
title: Plan File Sync Pattern
read_when:
  - editing PLAN-REVIEW files locally
  - syncing local plan changes to GitHub issues
  - working with plan feedback workflows
tripwires:
  - action: "Call plan-update-issue after editing local plan files"
    warning: "Sync is NOT automatic — GitHub issue will show stale content without explicit sync"
    score: 4
last_audited: "2026-02-08"
audit_result: edited
---

# Plan File Sync Pattern

Plan review PRs maintain plan content in two locations: a markdown file in the PR branch for version control, and a GitHub issue comment for structured review. These locations don't sync automatically — changes to the local file require an explicit sync command to propagate to the issue.

## Why Two Locations Don't Sync Automatically

Automatic sync (e.g., on every file save or commit) would create three problems:

1. **Race conditions**: Multiple edits in rapid succession would trigger overlapping API calls
2. **Partial updates**: Reviewers would see incomplete thoughts mid-edit
3. **Silent failures**: Network errors or API limits would corrupt state without agent awareness

Explicit sync gives agents **atomicity** (complete the edit, then sync) and **error handling** (detect and respond to sync failures).

## The Dual Storage Model

| Location       | Content                      | Purpose                  | Updated By        |
| -------------- | ---------------------------- | ------------------------ | ----------------- |
| **PR branch**  | `PLAN-REVIEW-{issue}.md`     | Version control history  | Git commit + push |
| **Issue body** | Comment with plan-body block | Reviewers see latest     | Sync command      |
| **Metadata**   | `plan_comment_id` field      | Tracks which comment     | Issue creation    |

The metadata field `plan_comment_id` in the issue's plan-header block stores the comment ID that contains the plan content. This allows the sync command to target the correct comment without searching.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py, extract_plan_header_comment_id -->
<!-- Source: src/erk/cli/commands/exec/scripts/plan_update_from_feedback.py, _update_plan_from_feedback_impl -->

See `extract_plan_header_comment_id()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` and `_update_plan_from_feedback_impl()` in `src/erk/cli/commands/exec/scripts/plan_update_from_feedback.py`.

## The Three-Step Workflow

After editing a plan file in response to review feedback:

1. **Commit changes** — `git add PLAN-REVIEW-{issue}.md && git commit && git push`
2. **Sync to issue** — `erk exec plan-update-issue --issue-number {issue} --plan-path PLAN-REVIEW-{issue}.md`
3. **Resolve threads** — Mark review comments as addressed

Step 2 is the critical sync. Without it, the PR updates but the issue comment remains stale.

<!-- Source: .claude/commands/erk/pr-address.md, Plan Review Phase 4 -->

See Plan Review Phase 4 in `.claude/commands/erk/pr-address.md` for the complete workflow integration.

## Validation Chain

The sync command performs LBYL validation before updating:

| Check                  | Error Type              | Why It Matters                                  |
| ---------------------- | ----------------------- | ----------------------------------------------- |
| Issue exists           | `issue_not_found`       | Can't sync to nonexistent issue                 |
| Has `erk-plan` label   | `missing_erk_plan_label` | Prevents syncing to wrong issue type            |
| Metadata has comment ID | `no_plan_comment_id`    | Can't target update without knowing which comment |
| Comment exists on issue | `comment_not_found`     | Tracked comment may have been deleted           |

Each validation raises a distinct error so agents can diagnose the failure without guessing.

## When to Sync vs When to Skip

### Sync when:

- Addressing review feedback (changes reviewers need to see)
- Regenerating sections based on codebase changes
- Adding missing details or clarifications
- Before resolving review threads (reviewers verify changes before thread closure)

### Skip when:

- Mid-edit (still drafting, not ready for reviewer visibility)
- Experimenting with ideas (will revert before finalizing)
- Working with file-based plans (no GitHub issue backing)
- Read-only operations (just reading the plan)

The decision point: **Will reviewers need to see this change to understand your response?**

## Comparison with Code PRs

Plan PRs diverge from code PRs in one critical way:

| Aspect         | Code PRs                     | Plan PRs                                 |
| -------------- | ---------------------------- | ---------------------------------------- |
| **Targets**    | PR branch only               | PR branch + issue comment                |
| **Sync**       | Git push (one target)        | Git push + sync command (two targets)    |
| **Review UI**  | PR diff                      | PR diff + issue comment (structured)     |
| **Why split?** | N/A                          | Issue provides canonical plan for querying |

The issue comment serves as the **canonical plan reference** for plan submission workflows — agents query the issue to get plan content, not the PR branch.

## Related Patterns

### Phase Zero Detection

Plan Review Mode in `/erk:pr-address` is triggered by detecting the `erk-plan-review` label on the PR. This label is auto-applied by `erk exec plan-create-review-pr`.

See [Phase Zero Detection Pattern](phase-zero-detection-pattern.md) for label-based workflow routing.

### Metadata Block System

Plan content is wrapped in `plan-body` markers (HTML comments) to separate it from surrounding metadata:

```markdown
<!-- plan-body -->
# Plan: Title
...
<!-- /plan-body -->
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py, format_plan_content_comment -->

This allows the issue to contain both plan content and dispatch/session metadata without conflict. See `format_plan_content_comment()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`.

## Related Documentation

- [PR-Based Plan Review Workflow](../planning/pr-review-workflow.md) — Complete plan review process
- [PR Address Workflows](../erk/pr-address-workflows.md) — Plan review mode vs code review mode
- [Phase Zero Detection Pattern](phase-zero-detection-pattern.md) — Label-based workflow routing

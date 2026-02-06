---
title: Draft PR Handling
read_when:
  - creating or working with draft PRs
  - understanding when to use draft status
  - converting between draft and ready for review
last_audited: "2026-02-05"
audit_result: edited
---

# Draft PR Handling

GitHub draft PRs signal work-in-progress. Use `gh pr create --fill --draft` to create, `gh pr ready` to mark ready for review.

## When to Use Draft Status

- Work is incomplete (implementation in progress, tests not written)
- Seeking early architectural feedback
- Iterating on CI fixes before requesting review
- Stacked PR dependencies (base PR not merged yet)

## Erk CI Behavior with Draft PRs

Erk's CI skips expensive checks for draft PRs via `github.event.pull_request.draft != true` conditions. Basic validation and security scans always run.

## Draft PRs in Stacked Workflows (Graphite)

- `gt submit --draft` creates all PRs in the stack as draft
- Base PR marked ready does not auto-mark dependent PRs ready
- After base merges, manually mark dependent PRs ready with `gh pr ready`

## Related Documentation

- [PR Submission Workflow](pr-submission-workflow.md) — Complete PR creation workflow

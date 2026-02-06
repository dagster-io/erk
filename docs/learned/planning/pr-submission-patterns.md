---
title: PR Submission Patterns
read_when:
  - "creating PRs programmatically"
  - "implementing idempotent PR submission"
  - "handling retry logic for PR operations"
last_audited: "2026-02-05"
audit_result: edited
---

# PR Submission Patterns

Patterns for reliable, idempotent PR creation and submission.

## Idempotent PR Submission

PR submission operations should be idempotent: running them multiple times produces the same result.

### Existing PR Detection

Before creating a PR, check if one already exists for the branch using `gh pr list --head "$BRANCH_NAME"`. Use `--head` flag for reliable branch-based discovery. If found, update the existing PR instead of creating a duplicate.

### Session-Scoped Idempotency

For session-aware operations (like plan-save), track created artifacts by session ID to prevent duplicate issues when retry loops occur.

## PR Body Validation (Iterate-Until-Valid)

When creating or updating PRs in erk, use the iterate-until-valid pattern:

1. Add known requirements (title, summary, checkout footer)
2. Run `erk pr check` to validate
3. Read error message carefully — messages indicate exactly what's missing
4. Fix and re-validate until passing

When validation errors are unclear, grep the codebase for the validator function name (e.g., `has_checkout_footer_for_pr`) to discover the exact regex pattern.

## Checkout Footer

Use plain text backtick format: `` `erk pr checkout <pr_number>` ``. The `has_checkout_footer_for_pr()` validation expects this format. See [PR Validation Rules](../pr-operations/pr-validation-rules.md) for details.

## Closing Reference

Issue closing keywords (`Closes #123`) must be in the **PR body** (not just commit messages) for GitHub auto-close to work. See [Issue-PR Closing Integration](../integrations/issue-pr-closing-integration.md).

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full plan lifecycle including PR creation
- [Submit Branch Reuse](submit-branch-reuse.md) - Branch reuse detection in plan submit
- [Source Code Investigation Pattern](debugging-patterns.md) - Debugging validation failures

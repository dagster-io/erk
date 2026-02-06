---
title: Issue-PR Closing Integration
read_when:
  - linking PRs to issues for auto-close
  - debugging why issues didn't close when PR merged
last_audited: "2026-02-05"
audit_result: edited
---

# Issue-PR Closing Integration

GitHub automatically closes issues when PRs merge if the PR description contains linking keywords (`Closes #123`, `Fixes #123`, etc.). Keywords must be in the PR body, not the title or commit messages.

## Erk Integration

Erk's PR submission pipeline handles issue closing references automatically:

- **Plan-based PRs**: `Closes #<issue_number>` is added using the issue number from `.impl/issue.json`
- **Cross-repo plans**: `Closes owner/repo#<issue_number>` format for plan issues in a separate repository
- **Validation**: `erk pr check` verifies the closing reference is present (see [PR Validation Rules](../pr-operations/pr-validation-rules.md))

## Debugging Auto-Close Failures

If an issue didn't close after PR merge:

1. Check PR body contains linking keyword: `gh pr view <pr> --json body --jq .body`
2. Verify PR merged to default branch: `gh pr view <pr> --json baseRefName --jq .baseRefName`
3. Confirm PR was merged (not just closed): `gh pr view <pr> --json merged --jq .merged`

## Related Documentation

- [PR Validation Rules](../pr-operations/pr-validation-rules.md) — Issue closing reference validation
- [Draft PR Handling](../pr-operations/draft-pr-handling.md) — Draft PR workflows

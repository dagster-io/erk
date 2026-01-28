---
title: Exec Command Patterns
read_when:
  - "working with plan issue metadata"
  - "extracting plan content from GitHub issues"
  - "implementing exec scripts that process plans"
---

# Exec Command Patterns

## Plan Content Extraction

### Reusable Functions

When building exec scripts that work with plan issues, reuse these existing functions rather than reimplementing:

**Location:** `src/erk/cli/commands/exec/scripts/plan_submit_for_review.py`

See the source file for:

- `extract_plan_header_comment_id(issue)` - Extracts the comment ID containing plan metadata from issue body
- `extract_plan_from_comment(comment)` - Parses plan content from a GitHub comment

### Common Flow

Both `plan_submit_for_review` and `plan_create_review_branch` use this pattern:

1. Fetch issue via `github_issues.get_issue(number)`
2. Check for `erk-plan` label
3. Extract plan comment ID via `extract_plan_header_comment_id()`
4. Fetch comment via `github_issues.get_comment(comment_id)`
5. Extract plan content via `extract_plan_from_comment()`

### Why This Matters

Reimplementing plan metadata extraction introduces:

- Parsing bugs (the metadata format has edge cases)
- Inconsistent error handling
- Maintenance burden when format changes

Always search for existing plan metadata functions before writing custom extraction.

## Related Topics

- [Exec Script Patterns](exec-script-patterns.md) - Template structure
- [erk exec Commands](erk-exec-commands.md) - Command reference

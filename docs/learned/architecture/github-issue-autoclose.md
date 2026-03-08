---
title: GitHub Issue Auto-Close Behavior (Historical)
read_when:
  - "understanding why erk no longer uses Closes #N"
  - "understanding plan closure strategy"
last_audited: "2026-02-26 12:00 PT"
audit_result: clean
---

# GitHub Issue Auto-Close Behavior (Historical)

Erk previously used `Closes #N` in PR bodies to auto-close plans on merge. This approach was abandoned due to unreliable behavior.

## Why "Closes #N" Was Removed

GitHub's `Closes #N` auto-close feature has critical quirks:

1. **Closing keywords must be present at PR creation time.** Adding `Closes #123` to a PR body after creation does NOT create the issue linkage.
2. **Auto-close is asynchronous.** There's a 1-3 second delay between PR merge and issue closure.
3. **Cross-repo references are fragile.** The `Closes owner/repo#123` format was frequently broken by PR body rewrites.

These issues caused frequent "issue didn't close" bugs that required retry logic and user-facing warnings.

## Current Strategy: Direct API Closure

Plans are now closed directly via the GitHub API during `erk land`:

- `check_and_display_plan_issue_closure()` in `objective_helpers.py` calls `plan_store.close_plan()` directly
- No dependency on PR body content
- No retry logic needed
- Deterministic and immediate

## Implementation Reference

- `src/erk/cli/commands/objective_helpers.py`: `check_and_display_plan_issue_closure()`

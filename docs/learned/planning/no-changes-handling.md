---
title: No Code Changes Handling
read_when:
  - "implementing erk-impl workflow"
  - "debugging no-changes scenarios"
  - "understanding erk-impl error handling"
---

# No Code Changes Handling

When the erk-impl workflow produces no code changes, it handles this gracefully by creating a diagnostic PR instead of failing.

## When This Occurs

Implementation may produce no code changes when:

- **Duplicate plan**: The same work was already implemented from another plan
- **Already merged**: The work landed in trunk through a different PR
- **Stale plan**: The plan addresses issues that have been resolved

## Workflow Response

Instead of failing, the workflow:

1. **Detects no changes**: Checks if the branch has any commits beyond the base
2. **Creates diagnostic PR**: Updates the PR body with diagnostic information
3. **Applies label**: Adds `no-changes` label (orange, `#FFA500`)
4. **Posts issue comment**: Notifies the plan issue with a link to the PR
5. **Exits gracefully**: Returns exit code 0 (success)

## Label Definition

| Label        | Color   | Description                             |
| ------------ | ------- | --------------------------------------- |
| `no-changes` | #FFA500 | Implementation produced no code changes |

## PR Body Content

The diagnostic PR body includes:

- Clear "No Code Changes" header
- Likely cause explanation (duplicate plan)
- How many commits behind trunk
- Recent commits on trunk (for comparison)
- Next steps for user resolution
- Link to workflow run

## User Resolution Steps

When encountering a no-changes PR:

1. **Review recent commits**: Check if the work appears in trunk
2. **If already done**: Close both the PR and the linked plan issue
3. **If not done**: Investigate why no changes were produced (plan may need revision)

## Exit Code Semantics

| Exit Code | Meaning                        |
| --------- | ------------------------------ |
| 0         | Success - PR updated and ready |
| 1         | Error - GitHub API failure     |

The workflow treats no-changes as a **successful completion**, not an error. This allows the workflow to mark the PR as ready for review so users can evaluate and close it.

## Implementation Reference

See `src/erk/cli/commands/exec/scripts/handle_no_changes.py`:

- `_build_pr_body()` - Generates diagnostic PR content
- `_build_issue_comment()` - Generates issue notification

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Phase 4 implementation details
- [erk-impl Customization](../ci/erk-impl-customization.md) - Workflow configuration

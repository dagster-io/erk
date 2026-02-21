# Fix: Replace "issue" with "plan" in implement command output

## Context

When running `erk implement` with the `draft_pr` backend, user-visible output messages say "issue" (e.g., "Detected GitHub issue #7720", "Fetching issue from GitHub...") even though the target is a draft PR, not an issue. The underlying code is correct — `ctx.plan_store` correctly delegates to the right backend — but the output strings are misleading.

The fix is simple: replace "issue" with "plan" in user-facing output strings. "Plan" is backend-agnostic and correct for both issue and draft_pr backends.

## Changes

### `src/erk/cli/commands/implement.py`

User-visible string replacements:

| Line | Old                                                            | New                                                           |
| ---- | -------------------------------------------------------------- | ------------------------------------------------------------- |
| 103  | `"Fetching issue from GitHub..."`                              | `"Fetching plan from GitHub..."`                              |
| 106  | `f"Issue #{issue_number} not found"`                           | `f"Plan #{issue_number} not found"`                           |
| 114  | `f"Issue #{issue_number} does not have the 'erk-plan' label."` | `f"Plan #{issue_number} does not have the 'erk-plan' label."` |
| 127  | `f"Issue: {plan.title}"`                                       | `f"Plan: {plan.title}"`                                       |
| 130  | `f"Would create .impl/ from issue #{issue_number}"`            | `f"Would create .impl/ from plan #{issue_number}"`            |
| 414  | `f"Detected GitHub issue #{target_info.issue_number}"`         | `f"Detected plan #{target_info.issue_number}"`                |

Docstring/comment updates adjacent to changed lines:

- Line 84: `"Implement feature from GitHub issue"` → `"Implement feature from plan"`
- Line 98: comment `"Discover repo context for issue fetch"` → `"Discover repo context for plan fetch"`

Help text in click command docstring (lines 329-343): Replace "GitHub issue" with "plan" where it refers to the abstract concept, keeping the URL pattern description accurate.

### `src/erk/cli/commands/implement_shared.py`

| Line | Old                                                   | New                                                  |
| ---- | ----------------------------------------------------- | ---------------------------------------------------- |
| 520  | `"Fetching issue from GitHub..."`                     | `"Fetching plan from GitHub..."`                     |
| 525  | `f"Error: Issue #{issue_number} not found"`           | `f"Error: Plan #{issue_number} not found"`           |
| 530  | `f"Issue: {plan.title}"`                              | `f"Plan: {plan.title}"`                              |
| 545  | `f"Would create worktree from issue #{issue_number}"` | `f"Would create worktree from plan #{issue_number}"` |

### `src/erk/cli/commands/branch/create_cmd.py`

| Line | Old                                                         | New                                                        |
| ---- | ----------------------------------------------------------- | ---------------------------------------------------------- |
| 279  | `f"Created .impl/ folder from issue #{setup.issue_number}"` | `f"Created .impl/ folder from plan #{setup.issue_number}"` |

### Out of scope

- Internal variable names (`issue_number`, `TargetInfo.issue_number`, etc.) — these are parameter names in function signatures and would be a larger refactor
- `detect_target_type()` return values (`"issue_number"`, `"issue_url"`) — internal enum-like values, not user-facing

## Verification

1. `pytest tests/ -k implement` — run existing implement tests to catch any string-matching regressions
2. `ruff check` / `ty check` — ensure no lint/type issues
3. Manual: `erk implement --dry-run 7720` should show "plan" instead of "issue" in output

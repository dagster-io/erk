---
title: Next Steps Output Formatting
read_when:
  - "modifying next-steps output after plan save or submit"
  - "understanding IssueNextSteps vs PlannedPRNextSteps"
  - "adding new next-steps commands to plan output"
tripwires:
  - action: "hardcoding next-steps command strings instead of using the dataclass properties"
    warning: "Use IssueNextSteps or PlannedPRNextSteps dataclasses from erk_shared.output.next_steps. They are the single source of truth for command formatting."
---

# Next Steps Output Formatting

After saving a plan, erk displays next-steps commands to the user. The formatting is centralized in a single module with two dataclasses for the two plan backends.

## Source

`packages/erk-shared/src/erk_shared/output/next_steps.py`

## Dataclasses

### `IssueNextSteps`

<!-- Source: packages/erk-shared/src/erk_shared/output/next_steps.py, IssueNextSteps -->

For issue-based plans. Takes `plan_number: int` and `url: str`. See `IssueNextSteps` in `packages/erk-shared/src/erk_shared/output/next_steps.py` for the full list of properties (view, checkout, dispatch, implement variants).

### `PlannedPRNextSteps`

<!-- Source: packages/erk-shared/src/erk_shared/output/next_steps.py, PlannedPRNextSteps -->

For draft-PR plans. Takes `pr_number: int`, `branch_name: str`, and `url: str`. See `PlannedPRNextSteps` in `packages/erk-shared/src/erk_shared/output/next_steps.py` for the full list of properties (identical to `IssueNextSteps`).

## Hierarchical Output Format

<!-- Source: packages/erk-shared/src/erk_shared/output/next_steps.py, format_next_steps_plain -->

The plain-text formatters produce a hierarchical format with three sections: "Implement plan" (with branch/worktree and dangerous variants), "Checkout plan" (branch/worktree), and "Dispatch to queue". See `format_next_steps_plain()` and `format_planned_pr_next_steps_plain()` in `packages/erk-shared/src/erk_shared/output/next_steps.py` for the exact output templates.

## Shell Activation Pattern

Both dataclasses use the `source "$(erk ... --script)"` pattern for commands that need to navigate the shell to a worktree. This is required because subprocess directory changes don't persist to the calling shell.

See [Shell Activation Pattern](../cli/shell-activation-pattern.md) for the full explanation.

## Format Functions

| Function                               | Context           | Output format |
| -------------------------------------- | ----------------- | ------------- |
| `format_next_steps_plain()`            | CLI (issue plans) | Plain text    |
| `format_planned_pr_next_steps_plain()` | CLI (draft plans) | Plain text    |
| `format_next_steps_markdown()`         | Issue body        | Markdown      |

## Slash Command Constants

Two slash command constants are defined for use in Claude Code context:

- `DISPATCH_SLASH_COMMAND = "/erk:pr-dispatch"` — used in the plain-text formatters for the "In Claude Code:" section
- `CHECKOUT_SLASH_COMMAND = "/erk:prepare"` — defined but not currently used in any formatter

## Related Topics

- [Shell Activation Pattern](../cli/shell-activation-pattern.md) - Why `source "$()"` is required
- [Draft PR Lifecycle](draft-pr-lifecycle.md) - Full lifecycle of draft-PR plans
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle

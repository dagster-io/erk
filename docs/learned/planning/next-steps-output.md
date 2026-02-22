---
title: Next Steps Output Formatting
read_when:
  - "modifying next-steps output after plan save or submit"
  - "understanding IssueNextSteps vs DraftPRNextSteps"
  - "adding new next-steps commands to plan output"
tripwires:
  - action: "hardcoding next-steps command strings instead of using the dataclass properties"
    warning: "Use IssueNextSteps or DraftPRNextSteps dataclasses from erk_shared.output.next_steps. They are the single source of truth for command formatting."
---

# Next Steps Output Formatting

After saving a plan, erk displays next-steps commands to the user. The formatting is centralized in a single module with two dataclasses for the two plan backends.

## Source

`packages/erk-shared/src/erk_shared/output/next_steps.py`

## Dataclasses

### `IssueNextSteps`

For issue-based plans. Takes `issue_number: int`.

| Property                         | Output                                                                                             |
| -------------------------------- | -------------------------------------------------------------------------------------------------- |
| `view`                           | `gh issue view {issue_number} --web`                                                               |
| `prepare`                        | `erk br co --for-plan {issue_number}`                                                              |
| `submit`                         | `erk plan submit {issue_number}`                                                                   |
| `prepare_and_implement`          | `source "$(erk br co --for-plan {issue_number} --script)" && erk implement --dangerous`            |
| `prepare_new_slot`               | `erk br co --new-slot --for-plan {issue_number}`                                                   |
| `prepare_new_slot_and_implement` | `source "$(erk br co --new-slot --for-plan {issue_number} --script)" && erk implement --dangerous` |

### `DraftPRNextSteps`

For draft-PR plans. Takes `pr_number: int` and `branch_name: str`.

| Property                         | Output                                                                                          |
| -------------------------------- | ----------------------------------------------------------------------------------------------- |
| `view`                           | `gh pr view {pr_number} --web`                                                                  |
| `submit`                         | `erk plan submit {pr_number}`                                                                   |
| `checkout_and_implement`         | `source "$(erk br co {branch_name} --script)" && erk implement --dangerous`                     |
| `prepare`                        | `erk br co --for-plan {pr_number}`                                                              |
| `prepare_and_implement`          | `source "$(erk br co --for-plan {pr_number} --script)" && erk implement --dangerous`            |
| `prepare_new_slot`               | `erk br co --new-slot --for-plan {pr_number}`                                                   |
| `prepare_new_slot_and_implement` | `source "$(erk br co --new-slot --for-plan {pr_number} --script)" && erk implement --dangerous` |

## Shell Activation Pattern

Both dataclasses use the `source "$(erk ... --script)"` pattern for commands that need to navigate the shell to a worktree. This is required because subprocess directory changes don't persist to the calling shell.

See [Shell Activation Pattern](../cli/shell-activation-pattern.md) for the full explanation.

## Format Functions

| Function                             | Context           | Output format |
| ------------------------------------ | ----------------- | ------------- |
| `format_next_steps_plain()`          | CLI (issue plans) | Plain text    |
| `format_draft_pr_next_steps_plain()` | CLI (draft plans) | Plain text    |
| `format_next_steps_markdown()`       | Issue body        | Markdown      |

## Slash Command Constants

Two slash command constants are defined for use in Claude Code context:

- `SUBMIT_SLASH_COMMAND = "/erk:plan-submit"` — used in the plain-text formatters for the "In Claude Code:" section
- `PREPARE_SLASH_COMMAND = "/erk:prepare"` — defined but not currently used in any formatter

## Related Topics

- [Shell Activation Pattern](../cli/shell-activation-pattern.md) - Why `source "$()"` is required
- [Draft PR Lifecycle](draft-pr-lifecycle.md) - Full lifecycle of draft-PR plans
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle

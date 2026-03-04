---
title: Next Steps Output Formatting
read_when:
  - "modifying next-steps output after plan save or submit"
  - "understanding PlanNextSteps"
  - "adding new next-steps commands to plan output"
tripwires:
  - action: "hardcoding next-steps command strings instead of using the dataclass properties"
    warning: "Use PlanNextSteps dataclass from erk_shared.output.next_steps. It is the single source of truth for command formatting."
---

# Next Steps Output Formatting

After saving a plan, erk displays next-steps commands to the user. The formatting is centralized in a single module with one dataclass.

## Source

`packages/erk-shared/src/erk_shared/output/next_steps.py`

## Dataclass

### `PlanNextSteps`

Takes `plan_number: int` and `url: str`.

| Property                         | Returns                                                                        |
| -------------------------------- | ------------------------------------------------------------------------------ |
| `view`                           | URL string                                                                     |
| `checkout`                       | `erk br co --for-plan {plan_number}`                                           |
| `dispatch`                       | `erk pr dispatch {plan_number}`                                                |
| `checkout_new_slot`              | `erk br co --new-slot --for-plan {plan_number}`                                |
| `implement_current_wt`           | `source "$(erk br co --for-plan {N} --script)" && erk implement`               |
| `implement_current_wt_dangerous` | `source "$(erk br co --for-plan {N} --script)" && erk implement -d`            |
| `implement_new_wt`               | `source "$(erk br co --new-slot --for-plan {N} --script)" && erk implement`    |
| `implement_new_wt_dangerous`     | `source "$(erk br co --new-slot --for-plan {N} --script)" && erk implement -d` |

## Hierarchical Output Format

The plain-text formatter (`format_plan_next_steps_plain`) produces a hierarchical format with three sections: "Implement plan" (with branch/worktree and dangerous variants), "Checkout plan" (branch/worktree), and "Dispatch to queue".

## Shell Activation Pattern

The dataclass uses the `source "$(erk ... --script)"` pattern for commands that need to navigate the shell to a worktree. This is required because subprocess directory changes don't persist to the calling shell.

See [Shell Activation Pattern](../cli/shell-activation-pattern.md) for the full explanation.

## Format Functions

| Function                         | Context    | Output format |
| -------------------------------- | ---------- | ------------- |
| `format_plan_next_steps_plain()` | CLI output | Plain text    |
| `format_next_steps_markdown()`   | PR body    | Markdown      |

## Slash Command Constants

Two slash command constants are defined for use in Claude Code context:

- `DISPATCH_SLASH_COMMAND = "/erk:pr-dispatch"` — used in the plain-text formatters for the "In Claude Code:" section
- `CHECKOUT_SLASH_COMMAND = "/erk:prepare"` — defined but not currently used in any formatter

## Related Topics

- [Shell Activation Pattern](../cli/shell-activation-pattern.md) - Why `source "$()"` is required
- [Draft PR Lifecycle](draft-pr-lifecycle.md) - Full lifecycle of draft-PR plans
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle

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

Properties return pre-formatted command strings. See the source file for the full list of available properties.

## Hierarchical Output Format

The plain-text formatter (`format_plan_next_steps_plain`) produces a hierarchical format with three sections: "Implement plan" (with branch/worktree and dangerous variants), "Checkout plan" (branch/worktree), and "Dispatch plan".

## Shell Activation Pattern

The dataclass uses the `source "$(erk ... --script)"` pattern for commands that need to navigate the shell to a worktree. This is required because subprocess directory changes don't persist to the calling shell.

See [Shell Activation Pattern](../cli/shell-activation-pattern.md) for the full explanation.

## Format Functions

| Function                         | Context                         | Output format |
| -------------------------------- | ------------------------------- | ------------- |
| `format_plan_next_steps_plain()` | CLI output, exit-plan-mode-hook | Plain text    |
| `format_next_steps_markdown()`   | PR body                         | Markdown      |

`format_plan_next_steps_plain()` is called in `exit_plan_mode_hook.py` when handling the plan-saved marker (Step 2 "what next?" output shown after saving a plan).

## `PlanNumberEvent`

<!-- Source: packages/erk-shared/src/erk_shared/core/prompt_executor.py -->

`PlanNumberEvent` is a typed event emitted by the prompt executor when Claude's output contains a plan number. It replaced the older `IssueNumberEvent` type:

```python
@dataclass(frozen=True)
class PlanNumberEvent:
    """Plan number."""
    number: int
```

`PlanNumberEvent.number` is a proper `int` (no string conversion needed). Contrast with `PrNumberEvent` which carries the PR number for created/updated PRs — both are in `erk_shared.core.prompt_executor` and are part of the `ExecutorEvent` union.

## Slash Command Constants

Two module-level slash command constants are defined but not directly used in any formatter. The plain-text formatter uses the `dispatch_slash_command` property on `PlanNextSteps` instead:

- `DISPATCH_SLASH_COMMAND = "/erk:pr-dispatch"` — not used in any formatter (the instance property `dispatch_slash_command` is used instead)
- `CHECKOUT_SLASH_COMMAND = "/erk:prepare"` — not used in any formatter

## Related Topics

- [Shell Activation Pattern](../cli/shell-activation-pattern.md) - Why `source "$()"` is required
- [Draft PR Lifecycle](draft-pr-lifecycle.md) - Full lifecycle of draft-PR plans
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle

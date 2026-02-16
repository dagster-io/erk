---
description: When to skip plan creation and execute directly
read_when:
  - considering entering plan mode
  - user rejected ExitPlanMode tool use
  - command provides explicit step-by-step instructions
tripwires:
  - action: "entering plan mode or using ExitPlanMode tool"
    warning: "Check if current task has explicit step-by-step instructions. If yes, skip planning and proceed directly to execution."
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# When to Skip Plan Mode

## The Pattern

Don't enter plan mode when explicit step-by-step instructions already exist.

Commands like `/erk:fix-conflicts` provide comprehensive instructions:

1. Read conflicted files
2. Analyze conflict type
3. Execute resolution strategy
4. Continue rebase

Creating a plan file adds overhead without value - the task is already decomposed.

## Heuristics

**Skip planning when:**

- Command documentation provides numbered steps
- User's prompt contains explicit instructions
- Task is mechanical execution of known steps

**Use planning when:**

- Task requires research or discovery
- Multiple approaches need evaluation
- Scope is unclear and needs decomposition

## Prevention

Before entering plan mode:

1. Check if current command provides step-by-step instructions
2. Check if user's prompt already decomposes the task
3. If yes to either: skip planning, proceed to execution

## Related

The analysis phase (reading files, understanding conflicts) remains valuable. Only the formalization into a plan document is redundant when instructions exist.

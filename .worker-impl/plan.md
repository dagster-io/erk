# Format one-shot instruction as `/erk:objective-next-plan` invocation

## Context

When `erk objective next-plan --one-shot` dispatches a step, the instruction in `.impl/task.md` is a generic description:

```
Implement step 1.1 of objective #7132: Audit score 12 docs (7 docs) (Phase: Phase 1)
```

The planning agent doesn't know it should use the `/erk:objective-next-plan` skill for guidance. The instruction should be formatted as a skill invocation so the agent knows what to load.

## Change

**File:** `src/erk/cli/commands/objective/next_plan_cmd.py` (lines 269-273)

Current:
```python
instruction = (
    f"Implement step {target_step.id} of objective #{issue_number}: "
    f"{target_step.description} (Phase: {target_phase.name})"
)
```

New:
```python
instruction = (
    f"/erk:objective-next-plan {issue_number}\n"
    f"Implement step {target_step.id} of objective #{issue_number}: "
    f"{target_step.description} (Phase: {target_phase.name})"
)
```

This produces:
```
/erk:objective-next-plan 7132
Implement step 1.1 of objective #7132: Audit score 12 docs (7 docs) (Phase: Phase 1)
```

## Verification

1. Run `make fast-ci` to verify no tests break
2. Run `erk objective next-plan <issue> --one-shot --dry-run` to see the new instruction format
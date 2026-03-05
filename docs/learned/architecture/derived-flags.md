---
title: Derived Flags Pattern
read_when:
  - "combining a user-provided flag with automatic detection"
  - "adding auto-behavior that should be transparent to the user"
  - "implementing --force auto-detection for plan implementations"
tripwires:
  - action: "auto-enabling a flag without informing the user"
    warning: "When deriving a flag from auto-detection, always print a dim-styled informational message explaining why the behavior was activated. Users should never be surprised by automatic actions."
---

# Derived Flags Pattern

When a boolean flag should be auto-enabled based on context (e.g., plan implementation always needs force-push), derive an **effective flag** that combines user intent with auto-detection.

## Pattern

```python
effective_flag = user_flag or auto_detected_condition
```

## Canonical Example: Auto-Force Push

In `src/erk/cli/commands/pr/submit_pipeline.py`:

```python
# Auto-force for plan implementations (branches always diverge from remote)
is_plan_impl = state.issue_number is not None
effective_force = state.force or is_plan_impl
```

**Why:** Plan implementation branches always diverge from remote because the draft PR scaffolding commits differ from the worker's implementation commits. Requiring `--force` every time would be a UX burden with no safety benefit.

## User Transparency

Always echo when auto-behavior activates:

```python
if is_plan_impl and not state.force:
    user_output(click.style(
        "  Auto-force enabled (plan implementation branch)",
        dim=True,
    ))
```

The dim styling signals informational output (not an error or warning).

## When to Use

- The flag has a clear auto-detection condition (not heuristic)
- The auto-detected case is always safe (no risk of data loss)
- The user would always pass the flag in that context anyway

## When NOT to Use

- The auto-detection is heuristic or could be wrong
- The flag controls a destructive operation where false positives matter
- The user should make an explicit choice

## Related Documentation

- [PR Submit Pipeline](../cli/pr-submit-pipeline.md) — Pipeline that uses this pattern
- [Planned PR Branch Teleport](../planning/planned-pr-branch-teleport.md) — Why plan branches diverge

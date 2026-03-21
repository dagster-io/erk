---
title: erk-learn Plan Dispatch
read_when:
  - "dispatching a learn plan for remote implementation"
  - "debugging why dispatch rejects a plan title"
  - "creating learn plans with the correct label"
tripwires:
  - action: "dispatching a plan with a title that has no [erk-pr] or [erk-learn] prefix"
    warning: "Both dispatch paths validate the title prefix. Plans must start with '[erk-pr] ' or '[erk-learn] ' to be dispatchable. Use erk exec plan-save --plan-type=learn for learn plans."
---

# erk-learn Plan Dispatch

## Title Prefix

Both `[erk-pr]` and `[erk-learn]` prefixes are accepted by `has_plan_title_prefix()` in `src/erk/cli/constants.py:10-12`:

```python
def has_plan_title_prefix(title: str) -> bool:
    """Return True if title starts with either [erk-pr] or [erk-learn] prefix."""
    return title.startswith(ERK_PR_TITLE_PREFIX) or title.startswith(ERK_LEARN_TITLE_PREFIX)
```

## Dispatch Compatibility

`dispatch_cmd.py:166-167` validates the title prefix before dispatching:

```python
if not has_plan_title_prefix(pr_result.title):
    # Error: plan must have [erk-pr] or [erk-learn] title prefix
```

Both regular plans and learn plans pass this check. The dispatch workflow treats them identically after validation.

## Label Assignment

The `erk-learn` label is added during plan-save with `--plan-type=learn`:

```bash
erk exec plan-save --plan-type=learn ...
```

In `plan_save.py:300-301`:

```python
if plan_type == "learn":
    labels.append("erk-learn")
```

The `erk-learn` label also triggers the `[erk-learn] ` title prefix (instead of `[erk-pr] `).

## Lifecycle

Learn plans follow the same dispatch/implement flow as regular plans:

1. `erk exec plan-save --plan-type=learn` → creates draft PR with `erk-learn` label
2. `erk pr dispatch <number>` → validates prefix, dispatches for remote implementation
3. Remote agent implements, submits PR
4. Land via normal flow

The only distinction is the `erk-learn` label (for filtering in TUI) and the `[erk-learn]` title prefix (for visual identification).

## Related Documentation

- [TUI Plan Title Rendering Pipeline](../tui/plan-title-rendering-pipeline.md) — How [erk-learn] prefix is displayed
- [Planned PR Backend](planned-pr-backend.md) — Title prefixing behavior

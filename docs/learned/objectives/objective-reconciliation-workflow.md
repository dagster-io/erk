---
title: Objective Reconciliation Workflow
read_when:
  - "running or debugging objective reconciliation"
  - "understanding how objective-plan triggers reconciliation"
  - "propagating --dangerous flag to Claude in objective workflows"
  - "working with the 6-phase reconcile audit flow"
tripwires:
  - action: "using None for allow_dangerous_override when dangerous=False"
    warning: "None-preservation is intentional. When dangerous=False, pass allow_dangerous_override=None (not False). This preserves the user's default config rather than forcing safe mode. See plan_cmd.py:730-733."
  - action: "replacing /erk:objective-reconcile with a Python CLI reconcile"
    warning: "Reconcile is an agent skill (.claude/commands/erk/objective-reconcile.md), not a Python CLI command. The skill runs Claude's search/verification capabilities. erk objective reconcile (Python) is the user-facing entry point."
---

# Objective Reconciliation Workflow

## What

Objective reconciliation audits an open objective against the current codebase state. It identifies stale references, already-done work, and outdated descriptions in the objective's roadmap nodes.

## When

- **Automatically**: Runs as Step 2.5 in `/erk:objective-plan` (before node selection)
- **Manually**: Via `erk objective reconcile <number>` or `/erk:objective-reconcile <number>`

## 6 Phases

The reconciliation workflow (`.claude/commands/erk/objective-reconcile.md`, 285 lines) runs through 6 phases:

| Phase | Name     | What Happens                                                                             |
| ----- | -------- | ---------------------------------------------------------------------------------------- |
| 1     | Validate | Fetch objective, verify `erk-objective` label, warn if CLOSED                            |
| 2     | Extract  | Build checklist of auditable references (file paths, commands, functions, pending nodes) |
| 3     | Verify   | Check each reference against codebase via Glob/Grep/gh search                            |
| 4     | Findings | Present structured table of findings to user                                             |
| 5     | Propose  | Generate minimal update diff for STALE and DONE items                                    |
| 6     | Execute  | Apply approved updates via `erk exec update-objective`                                   |

## Finding Types

| Status    | Meaning                                                   |
| --------- | --------------------------------------------------------- |
| `CURRENT` | Reference is accurate, exists as described                |
| `STALE`   | Reference points to something renamed, moved, or deleted  |
| `DONE`    | Pending node whose work was accomplished via other PRs    |
| `UNCLEAR` | Cannot determine status automatically; needs human review |

## Dangerous Mode Propagation

The `-d/--dangerous` flag on `erk objective plan` propagates to Claude's permission mode. The None-preservation pattern at `plan_cmd.py:730-733`:

```python
if dangerous:
    allow_dangerous_override = True
else:
    allow_dangerous_override = None  # NOT False — preserves user config default
```

- `dangerous=True` → `dangerous_override=True, allow_dangerous_override=True`
- `dangerous=False` → `dangerous_override=None, allow_dangerous_override=None`

Using `None` instead of `False` preserves the user's default config rather than forcing safe mode when the flag is absent.

## Auto-Reconcile in objective-plan

When `/erk:objective-plan` runs (Step 2.5), it invokes reconciliation before presenting node selection:

```
1. Run /erk:objective-reconcile <objective-number>
2. If no issues: "all references current" — continue to node selection
3. If STALE/DONE found: show findings, propose updates, apply if approved
4. Continue with objective-plan after reconciliation
```

Source: `.claude/commands/erk/objective-plan.md:28, 72-78`

## Related Documentation

- [Objective Plan Workflow](../planning/workflow.md) — How plans are created from objectives

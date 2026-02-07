---
title: Workflow Markers
read_when:
  - "building multi-step workflows that need state persistence"
  - "using erk exec marker commands"
  - "implementing objective-to-plan workflows"
---

# Workflow Markers

Markers persist state across workflow steps when a single session needs to pass information between distinct phases.

## Commands

- `erk exec marker create --name <name> --value <value>` - Create/update a marker
- `erk exec marker read --name <name>` - Read marker value (empty if not set)

## Use Cases

### Objective Context

When creating a plan from an objective step, markers track the objective for later hooks:

```bash
erk exec marker create --name objective-context --value "5503"
erk exec marker create --name roadmap-step --value "1B.4"
```

The `exit-plan-mode` hook reads `objective-context` to update the objective issue when the plan is saved.

### Workflow State

For multi-phase workflows where information from step N is needed in step N+2:

1. Early step writes marker with computed value
2. Later step reads marker to continue workflow

## Design Principles

- Markers are session-scoped (tied to `CLAUDE_SESSION_ID`)
- Use descriptive names: `objective-context`, `roadmap-step`, `selected-branch`
- Markers survive hook boundaries but not session restarts

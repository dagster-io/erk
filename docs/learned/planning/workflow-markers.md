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

### Plan Issue Tracking

When saving a plan to GitHub for review, markers communicate the issue number between commands:

```bash
# Created by /erk:plan-save
erk exec marker create --name plan-saved-issue --value "6425"

# Read by /erk:plan-review to create review PR
ISSUE_NUM=$(erk exec marker read --name plan-saved-issue)
```

Lifecycle:

1. `/erk:plan-save` saves plan to GitHub, creates issue, writes `plan-saved-issue` marker
2. User (or automation) reads marker to get issue number
3. `/erk:plan-review <issue-number>` creates review PR for the saved plan
4. Marker persists for the session, enabling multiple review PR iterations if needed

This enables the "Save and submit for review" workflow (Option E) where plans are saved and reviewed via PR before implementation.

### Workflow State

For multi-phase workflows where information from step N is needed in step N+2:

1. Early step writes marker with computed value
2. Later step reads marker to continue workflow

## Design Principles

- Markers are session-scoped (tied to `CLAUDE_SESSION_ID`)
- Use descriptive names: `objective-context`, `roadmap-step`, `selected-branch`
- Markers survive hook boundaries but not session restarts

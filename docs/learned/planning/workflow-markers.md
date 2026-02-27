---
title: Workflow Markers
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
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

The `plan-save` command reads `objective-context` directly to link the plan to its objective. The `roadmap-step` marker provides the specific node ID being planned.

The `objective-context` marker is the PRIMARY mechanism for objective linking — there is no CLI flag alternative. It must be created before entering plan mode (step 5 of objective-plan), before gathering code context. If missing, plan-save cannot call update-objective-node, and the objective roadmap table silently fails to update.

### Plan Issue Tracking

When saving a plan to GitHub, markers communicate the issue number between commands:

```bash
# Created by /erk:plan-save
erk exec marker create --name plan-saved-issue --value "6425"

# Read by subsequent commands to reference the saved plan
ISSUE_NUM=$(erk exec marker read --name plan-saved-issue)
```

Lifecycle:

1. `/erk:plan-save` saves plan to GitHub, creates issue, writes `plan-saved-issue` marker
2. User (or automation) reads marker to get issue number
3. Marker persists for the session, enabling subsequent operations on the saved plan

### Workflow State

For multi-phase workflows where information from step N is needed in step N+2:

1. Early step writes marker with computed value
2. Later step reads marker to continue workflow

## Design Principles

- Markers are session-scoped (tied to `CLAUDE_SESSION_ID`)
- Use descriptive names: `objective-context`, `roadmap-step`, `selected-branch`
- Markers survive hook boundaries but not session restarts

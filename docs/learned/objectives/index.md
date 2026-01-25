---
title: Objectives Package
read_when:
  - "working with objectives"
  - "understanding objective step inference"
  - "implementing auto-advance workflows"
  - "using reconciler or roadmap parser"
tripwires:
  - action: "accessing PR column value without checking Status column first"
    warning: "Status column (blocked, skipped) overrides PR column inference. Always check Status column first or data will be lost."
  - action: "adding new step status values to StepStatus"
    warning: "New statuses must be explicitly handled in get_next_actionable_step() or they may unintentionally block forward progress."
---

# Objectives Package

The objectives package provides LLM-based analysis of objective roadmaps. It enables automatic detection of the next actionable step in a multi-step objective.

## Package Location

```
packages/erk-shared/src/erk_shared/objectives/
├── __init__.py
├── types.py            # Core types: NextStepResult, InferenceError, ReconcileAction
├── roadmap_parser.py   # Parse roadmap tables from issue body
├── next_step_inference.py  # LLM-based step inference
└── reconciler.py       # Determine next action for an objective
```

## Key Types

### NextStepResult

Result of inferring the next actionable step from an objective:

| Field              | Type   | Description                                        |
| ------------------ | ------ | -------------------------------------------------- | ------------------------------------------------- |
| `has_next_step`    | `bool` | Whether an actionable step is available            |
| `step_id`          | `str   | None`                                              | Step identifier (e.g., "1.1", "2A.1")             |
| `step_description` | `str   | None`                                              | Human-readable description                        |
| `phase_name`       | `str   | None`                                              | Phase containing this step (e.g., "Phase 1: ...") |
| `reason`           | `str`  | Why this step was chosen, or why no step available |

### InferenceError

Error during LLM inference (rate limit, network error, auth failure):

| Field     | Type  | Description                  |
| --------- | ----- | ---------------------------- |
| `message` | `str` | Human-readable error message |

### ReconcileAction

Action determined by the reconciler:

| Field              | Type  | Description                       |
| ------------------ | ----- | --------------------------------- | --------------------------------------- |
| `action_type`      | `str` | "create_plan", "none", or "error" |
| `step_id`          | `str  | None`                             | Step ID if action_type is "create_plan" |
| `step_description` | `str  | None`                             | Step description                        |
| `phase_name`       | `str  | None`                             | Phase name                              |
| `reason`           | `str` | Human-readable explanation        |

## PR Column Format

Objective roadmaps use a non-standard PR column format:

| Column Value | Meaning                        |
| ------------ | ------------------------------ |
| (empty)      | Step is pending                |
| `#XXXX`      | Step done (merged PR)          |
| `plan #XXXX` | Plan in progress for this step |

This is an erk-specific convention, not a GitHub standard.

## Status Column Override

**Critical**: The Status column overrides PR column inference.

If a step has `blocked` or `skipped` in the Status column, that takes precedence over any PR column value. Always check Status column first when determining step state.

## Cost Model

- **Inference**: Uses Haiku model (~$0.001/call)
- Designed for high-volume automated use

## When to Use

- Auto-advancing objective workflows after PR landing
- Determining next actionable step in multi-phase objectives
- Reconciling objective state with current codebase

## CLI Commands

```bash
# Infer next step from objective
erk objective next-step <objective-issue>

# Get roadmap steps
erk exec get-objective-steps <objective-issue>
```

## Related Documentation

- [Glossary: Objectives System](../glossary.md#objectives-system) - Definitions for objective, turn, etc.
- [Plan Lifecycle](../planning/lifecycle.md) - How plans integrate with objectives

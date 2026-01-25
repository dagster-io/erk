---
title: Plan Generation Workflow
read_when:
  - "generating plans from objective steps"
  - "working with generate_plan_for_step function"
  - "understanding objective-to-plan conversion"
  - "implementing plan creation from roadmap steps"
---

# Plan Generation Workflow

LLM-based generation of implementation plans from objective steps. Plans are markdown documents that can be saved to GitHub issues via `create_plan_issue()`.

## Overview

When the reconciler identifies an actionable step in an objective roadmap, the plan generator creates a structured implementation plan. This plan contains:

- Context extracted from the objective
- Design decisions inherited from the parent objective
- Specific files to modify
- Test requirements

## Function Signature

The core function is `generate_plan_for_step()` in `packages/erk-shared/src/erk_shared/objectives/plan_generator.py`:

```python
def generate_plan_for_step(
    executor: PromptExecutor,
    *,
    objective_body: str,
    objective_number: int,
    step_id: str,
    step_description: str,
    phase_name: str,
) -> GeneratedPlan | PlanGenerationError:
```

### Parameters

| Parameter          | Type             | Description                                   |
| ------------------ | ---------------- | --------------------------------------------- |
| `executor`         | `PromptExecutor` | Gateway for LLM prompt execution              |
| `objective_body`   | `str`            | Full markdown of the objective issue          |
| `objective_number` | `int`            | Issue number for linking                      |
| `step_id`          | `str`            | Step identifier (e.g., "1.1", "2A.1")         |
| `step_description` | `str`            | Human-readable description of the step        |
| `phase_name`       | `str`            | Phase containing this step (e.g., "Phase 1:") |

### Return Types

Uses discriminated union pattern for error handling:

- **`GeneratedPlan`**: Success case with `content` (markdown) and `title` fields
- **`PlanGenerationError`**: Failure case with `message` field

## Generated Plan Structure

The prompt instructs Haiku to generate plans with this structure:

```markdown
# <Plan Title Based on Step Description>

**Part of Objective #N, Step X.X**

## Goal

<Brief description of what this step accomplishes>

## Implementation Approach

### Design Decisions

<Any design decisions inferred from the objective context>

---

## Phase 1: <Phase Name>

### Files to Create/Modify

<List files and what changes are needed>

### Tests

<Describe test requirements>

---

## Verification

<How to verify the implementation>

---

## Dependencies

- Requires: `dignified-python` skill
- Requires: `fake-driven-testing` skill
```

## Title Extraction

The `_extract_plan_title()` helper extracts the H1 title from generated content. If no H1 is found, it falls back to `Step {step_id}: {step_description}`.

## Cost Model

Uses Haiku model for generation: ~$0.001 per plan generated.

## Integration with Reconciliation

The plan generator is called by the reconciler when:

1. `NextStepResult.has_next_step` is `True`
2. A step is identified as actionable (not blocked, not in progress)
3. The step's PR column is empty

Typical flow:

1. Reconciler identifies next actionable step
2. Plan generator creates plan markdown
3. Plan is saved to GitHub issue via `create_plan_issue()`
4. Roadmap is updated with `plan #N` reference

## Example Usage

```python
from erk_shared.objectives.plan_generator import (
    generate_plan_for_step,
    GeneratedPlan,
    PlanGenerationError,
)
from erk_shared.prompt_executor.real import RealPromptExecutor
from erk_shared.gateway.time.real import RealTime

executor = RealPromptExecutor(time=RealTime())
result = generate_plan_for_step(
    executor,
    objective_body=objective_issue.body,
    objective_number=objective_issue.number,
    step_id="1.1",
    step_description="Add gateway ABC for new service",
    phase_name="Phase 1: Infrastructure",
)

if isinstance(result, PlanGenerationError):
    click.echo(f"Failed: {result.message}")
else:
    # result is GeneratedPlan
    issue = create_plan_issue(result.content, result.title)
```

## Testing

Use `FakePromptExecutor` to test plan generation:

```python
from erk_shared.prompt_executor.fake import FakePromptExecutor

executor = FakePromptExecutor(output="# Test Plan\n\n## Goal\n\nTest goal")
result = generate_plan_for_step(executor, ...)
assert isinstance(result, GeneratedPlan)
assert result.title == "Test Plan"
```

## Related Documentation

- [Objectives Package](index.md) - Overview of objectives system
- [Prompt Executor Gateway](../architecture/prompt-executor-gateway.md) - PromptExecutor interface
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Error handling pattern
- [Roadmap Updates](../planning/roadmap-updates.md) - How roadmaps are updated after plan creation

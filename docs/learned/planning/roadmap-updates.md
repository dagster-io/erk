---
title: Roadmap Updates
read_when:
  - "updating objective roadmap tables"
  - "working with update_roadmap_with_plan function"
  - "adding plan references to roadmap steps"
  - "understanding PR column format in objectives"
---

# Roadmap Updates

LLM-based updates to objective roadmap tables. When a plan is created for an objective step, the roadmap's PR column is updated to show `plan #N`.

## Overview

Objective issues contain roadmap tables tracking step progress. When a plan is created for a step, the roadmap must be updated to reflect the in-progress state. This module uses Haiku to reliably update tables across various markdown formats.

## PR Column Format

Objective roadmaps use a non-standard PR column format (erk-specific):

| Column Value | Meaning                        |
| ------------ | ------------------------------ |
| (empty)      | Step is pending                |
| `#XXXX`      | Step is done (merged PR)       |
| `plan #XXXX` | Plan in progress for this step |

## Function Signature

The core function is `update_roadmap_with_plan()` in `packages/erk-shared/src/erk_shared/objectives/roadmap_updater.py`:

```python
def update_roadmap_with_plan(
    executor: PromptExecutor,
    objective_body: str,
    *,
    step_id: str,
    plan_issue_number: int,
) -> RoadmapUpdateResult:
```

### Parameters

| Parameter           | Type             | Description                               |
| ------------------- | ---------------- | ----------------------------------------- |
| `executor`          | `PromptExecutor` | Gateway for LLM prompt execution          |
| `objective_body`    | `str`            | Full markdown body of the objective issue |
| `step_id`           | `str`            | Step identifier to update (e.g., "1.1")   |
| `plan_issue_number` | `int`            | Plan issue number to add                  |

### Return Type

```python
@dataclass(frozen=True)
class RoadmapUpdateResult:
    success: bool
    updated_body: str | None  # New markdown if successful
    error: str | None         # Error message if failed
```

## How It Works

1. **Prompt Construction**: Builds a prompt instructing Haiku to find and update the step
2. **LLM Execution**: Sends prompt via PromptExecutor
3. **Response Parsing**: Checks for `ERROR:` prefix or validates update marker
4. **Result Return**: Returns updated body or error information

## Update Rules

The LLM follows strict rules:

1. Find the row where Step column exactly matches the step_id
2. The PR column for that row must currently be empty
3. Add `plan #N` to that PR column
4. Preserve ALL other content exactly (other rows, columns, text before/after tables)
5. If step not found or PR column not empty, return `ERROR: <reason>`

## Validation

The `_parse_updater_response()` helper validates that the LLM response:

- Does NOT start with `ERROR:`
- Contains the expected `plan #` marker

If validation fails, the result indicates failure with an appropriate error message.

## Cost Model

Uses Haiku model: ~$0.001 per update.

## Why LLM-Based?

Previous approaches using regex failed on:

- Multiple tables in one objective
- Varying table formats (alignment, spacing)
- Complex markdown with nested structures
- Objectives with multiple phases

Haiku reliably handles these edge cases while maintaining exact formatting.

## Example Usage

```python
from erk_shared.objectives.roadmap_updater import (
    update_roadmap_with_plan,
    RoadmapUpdateResult,
)
from erk_shared.prompt_executor.real import RealPromptExecutor
from erk_shared.gateway.time.real import RealTime

executor = RealPromptExecutor(time=RealTime())
result = update_roadmap_with_plan(
    executor,
    objective_body=objective_issue.body,
    step_id="1.1",
    plan_issue_number=456,
)

if result.success:
    # Update the issue with new body
    github.update_issue_body(objective_number, result.updated_body)
else:
    click.echo(f"Failed to update roadmap: {result.error}")
```

## Integration with Plan Creation

Typical workflow when reconciler creates a plan:

1. `generate_plan_for_step()` creates plan markdown
2. `create_plan_issue()` creates GitHub issue
3. **`update_roadmap_with_plan()`** updates objective roadmap
4. Now step shows `plan #N` in PR column

## Error Cases

| Error                         | Cause                                   |
| ----------------------------- | --------------------------------------- |
| "Step not found"              | Step ID doesn't exist in any table      |
| "PR column not empty"         | Step already has a PR or plan reference |
| "LLM response missing marker" | Haiku didn't include `plan #` in output |
| Prompt execution failure      | Network error, rate limit, etc.         |

## Testing

Use `FakePromptExecutor` to test roadmap update logic:

```python
from erk_shared.prompt_executor.fake import FakePromptExecutor

# Simulate successful update
updated_body = original_body.replace("| 1.1 | Do thing |  |", "| 1.1 | Do thing | plan #456 |")
executor = FakePromptExecutor(output=updated_body)
result = update_roadmap_with_plan(executor, original_body, step_id="1.1", plan_issue_number=456)
assert result.success

# Simulate error case
executor = FakePromptExecutor(output="ERROR: Step 1.1 not found in roadmap")
result = update_roadmap_with_plan(executor, original_body, step_id="1.1", plan_issue_number=456)
assert not result.success
assert "not found" in result.error
```

## Related Documentation

- [Objectives Package](../objectives/index.md) - Overview of objectives system
- [Plan Generation Workflow](../objectives/plan-generation-workflow.md) - Creating plans from steps
- [Prompt Executor Gateway](../architecture/prompt-executor-gateway.md) - PromptExecutor interface
- [Glossary: PR Column Format](../glossary.md) - PR column value definitions

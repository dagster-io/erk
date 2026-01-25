"""LLM-based plan generation for objective steps.

This module generates implementation plan markdown from objective step context
using Claude Haiku. The generated plan can then be used with create_plan_issue()
to create a GitHub issue.

Cost: ~$0.001 per generation (Haiku model)
"""

from dataclasses import dataclass

from erk_shared.prompt_executor.abc import PromptExecutor


@dataclass(frozen=True)
class GeneratedPlan:
    """Result of generating a plan from an objective step.

    Attributes:
        content: The full plan markdown content suitable for create_plan_issue()
        title: The extracted title for the plan issue
    """

    content: str
    title: str


@dataclass(frozen=True)
class PlanGenerationError:
    """Error during plan generation.

    Attributes:
        message: Human-readable error description
    """

    message: str


# Prompt template for plan generation
_PLAN_GENERATION_PROMPT = """Generate an implementation plan for this objective step.

OBJECTIVE CONTEXT:
{objective_body}

STEP TO IMPLEMENT:
- Step ID: {step_id}
- Description: {step_description}
- Phase: {phase_name}
- Parent Objective: #{objective_number}

OUTPUT FORMAT:
Generate a plan markdown document with the following structure:

# <Plan Title Based on Step Description>

**Part of Objective #{objective_number}, Step {step_id}**

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

IMPORTANT:
- Extract relevant context from the objective (design decisions, related files)
- Be specific about files to modify and changes needed
- Include test requirements
- Keep the plan focused on this single step
"""


def generate_plan_for_step(
    executor: PromptExecutor,
    *,
    objective_body: str,
    objective_number: int,
    step_id: str,
    step_description: str,
    phase_name: str,
) -> GeneratedPlan | PlanGenerationError:
    """Generate a plan markdown document for a specific objective step.

    Uses Haiku to create a structured plan based on:
    - The step context from the objective
    - Design decisions from the objective
    - Related files and patterns mentioned

    Args:
        executor: PromptExecutor for running the LLM prompt
        objective_body: The full markdown body of the objective issue
        objective_number: The objective issue number for linking
        step_id: The step identifier (e.g., "1.1", "2A.1")
        step_description: Description of the step
        phase_name: The phase containing this step

    Returns:
        GeneratedPlan on success with plan content and title,
        or PlanGenerationError if the LLM call failed.
    """
    prompt = _PLAN_GENERATION_PROMPT.format(
        objective_body=objective_body,
        objective_number=objective_number,
        step_id=step_id,
        step_description=step_description,
        phase_name=phase_name,
    )

    result = executor.execute_prompt(prompt, model="haiku")

    if not result.success:
        return PlanGenerationError(message=result.error or "Unknown error")

    plan_content = result.output.strip()
    title = _extract_plan_title(plan_content, step_id, step_description)

    return GeneratedPlan(content=plan_content, title=title)


def _extract_plan_title(
    plan_content: str,
    step_id: str,
    step_description: str,
) -> str:
    """Extract title from plan content or generate from step info.

    Tries to extract the H1 title from the plan content. Falls back to
    generating a title from step info if no H1 is found.

    Args:
        plan_content: The generated plan markdown
        step_id: The step identifier
        step_description: Description of the step

    Returns:
        Extracted or generated title
    """
    # Try to extract H1 title from plan content
    for line in plan_content.split("\n"):
        line = line.strip()
        if line.startswith("# ") and len(line) > 2:
            return line[2:].strip()

    # Fallback: generate title from step info
    return f"Step {step_id}: {step_description}"

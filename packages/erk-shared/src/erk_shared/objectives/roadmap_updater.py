"""Update objective roadmap tables with plan references.

This module uses LLM inference to update the PR column of objective roadmap
tables when a plan is created for a step. The LLM approach handles objectives
with multiple tables/phases more reliably than regex-based parsing.

PR column format (erk-specific):
- Empty: step is pending
- #XXXX: step is done (merged PR number)
- plan #XXXX: plan in progress (plan issue number)

Cost: ~$0.001 per roadmap update (Haiku model)
"""

from dataclasses import dataclass

from erk_shared.prompt_executor.abc import PromptExecutor

# Prompt template for Haiku roadmap update
UPDATER_PROMPT = """Update this objective's roadmap table.
Add 'plan #{plan_number}' to the PR column for step '{step_id}'.

Rules:
1. Find the row where the Step column exactly matches '{step_id}'
2. The PR column for that row must currently be empty
3. Add 'plan #{plan_number}' to that PR column
4. Preserve ALL other content exactly (other rows, other columns, text before/after tables)
5. If the step is not found or PR column is not empty, respond with ERROR: <reason>

Respond with either:
- The complete updated markdown body (preserving exact formatting)
- ERROR: <reason> if the update cannot be made

OBJECTIVE BODY:
{objective_body}
"""


@dataclass(frozen=True)
class RoadmapUpdateResult:
    """Result of updating objective roadmap.

    Attributes:
        success: Whether the update succeeded
        updated_body: The updated markdown body if successful, None otherwise
        error: Error message if failed, None otherwise
    """

    success: bool
    updated_body: str | None
    error: str | None


def update_roadmap_with_plan(
    executor: PromptExecutor,
    objective_body: str,
    *,
    step_id: str,
    plan_issue_number: int,
) -> RoadmapUpdateResult:
    """Update the PR column of a roadmap step to show 'plan #N'.

    Uses Haiku LLM inference to find the step across all tables in the
    objective and update its PR column.

    Args:
        executor: PromptExecutor for running the LLM prompt
        objective_body: The full markdown body of the objective issue
        step_id: The step identifier to find (e.g., "1.1", "2A.1")
        plan_issue_number: The plan issue number to add

    Returns:
        RoadmapUpdateResult with updated body on success, error message on failure.

    Notes:
        - Only updates if PR column is currently empty
        - Step ID matching is exact (case-sensitive)
        - Works across multiple tables/phases in the objective
    """
    prompt = UPDATER_PROMPT.format(
        plan_number=plan_issue_number,
        step_id=step_id,
        objective_body=objective_body,
    )

    result = executor.execute_prompt(prompt, model="haiku")

    if not result.success:
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error=result.error or "Unknown error",
        )

    return _parse_updater_response(result.output, step_id)


def _parse_updater_response(output: str, step_id: str) -> RoadmapUpdateResult:
    """Parse the LLM response to extract updated body or error.

    Args:
        output: The raw text output from Haiku.
        step_id: The step identifier (for error messages).

    Returns:
        RoadmapUpdateResult with parsed content.
    """
    output_stripped = output.strip()

    # Check for ERROR prefix
    if output_stripped.startswith("ERROR:"):
        error_message = output_stripped[6:].strip()
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error=error_message,
        )

    # Validate the response contains the expected update
    expected_marker = f"plan #{step_id}" if step_id.isdigit() else "plan #"
    if expected_marker not in output_stripped and "plan #" not in output_stripped:
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error=f"LLM response missing expected 'plan #' marker for step {step_id}",
        )

    return RoadmapUpdateResult(
        success=True,
        updated_body=output_stripped,
        error=None,
    )

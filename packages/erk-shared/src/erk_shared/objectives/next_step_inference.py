"""LLM-based inference for determining the next actionable step from an objective.

This module uses Claude Haiku to analyze an objective's roadmap and determine
which step should be worked on next. The LLM approach is more flexible and
maintainable than regex-based parsing.

Cost: ~$0.001 per inference (Haiku model)
"""

from erk_shared.objectives.types import InferenceError, NextStepResult
from erk_shared.prompt_executor.abc import PromptExecutor

# Prompt template for Haiku inference
INFERENCE_PROMPT = """Analyze this objective and determine the next actionable step.

Rules for determining the next step:
1. A step is "done" if its PR column contains "#" followed by a number (e.g., "#5892")
2. A step has a "plan in progress" if its PR column contains "plan #" (e.g., "plan #5935")
3. A step is "blocked" if its Status column says "blocked"
4. A step is "pending" if its PR column is empty and Status is not blocked

Find the FIRST step where:
- The previous step (if any) is done
- This step is pending (not done, not blocked, not plan-in-progress)

Respond in this exact format (each field on its own line):
NEXT_STEP: <yes or no>
STEP_ID: <step id like "1.1" or "2A.1", or "none">
DESCRIPTION: <step description, or "none">
PHASE: <phase name, or "none">
REASON: <brief explanation>

OBJECTIVE:
{objective_body}
"""


def infer_next_step(
    executor: PromptExecutor,
    objective_body: str,
) -> NextStepResult | InferenceError:
    """Use Haiku to infer the next actionable step from an objective.

    Args:
        executor: PromptExecutor for running the LLM prompt.
        objective_body: The full markdown body of the objective issue.

    Returns:
        NextStepResult on successful inference (even if no step found),
        or InferenceError if the LLM call failed.
    """
    prompt = INFERENCE_PROMPT.format(objective_body=objective_body)

    result = executor.execute_prompt(prompt, model="haiku")

    if not result.success:
        return InferenceError(message=result.error or "Unknown error")

    return _parse_inference_response(result.output)


def _parse_inference_response(output: str) -> NextStepResult:
    """Parse the structured text response from Haiku.

    Extracts fields from the response using simple line parsing. The response
    format is strictly defined in the prompt to ensure reliable parsing.

    Args:
        output: The raw text output from Haiku.

    Returns:
        NextStepResult with parsed fields.
    """
    fields = _extract_fields(output)

    has_next_step = fields.get("NEXT_STEP", "").lower() == "yes"

    # Extract optional fields, treating "none" as None
    step_id = _normalize_optional(fields.get("STEP_ID", ""))
    step_description = _normalize_optional(fields.get("DESCRIPTION", ""))
    phase_name = _normalize_optional(fields.get("PHASE", ""))
    reason = fields.get("REASON", "No reason provided")

    return NextStepResult(
        has_next_step=has_next_step,
        step_id=step_id,
        step_description=step_description,
        phase_name=phase_name,
        reason=reason,
    )


def _extract_fields(output: str) -> dict[str, str]:
    """Extract key-value fields from the response.

    Parses lines in the format "KEY: value" into a dictionary.
    Handles multi-word values and preserves case in values.

    Args:
        output: The raw text output from Haiku.

    Returns:
        Dictionary mapping field names to their values.
    """
    fields: dict[str, str] = {}

    for line in output.strip().split("\n"):
        if ":" not in line:
            continue

        # Split on first colon only to preserve colons in values
        key, _, value = line.partition(":")
        key = key.strip().upper()
        value = value.strip()

        # Only capture known fields
        if key in {"NEXT_STEP", "STEP_ID", "DESCRIPTION", "PHASE", "REASON"}:
            fields[key] = value

    return fields


def _normalize_optional(value: str) -> str | None:
    """Normalize optional field value.

    Converts "none" (case-insensitive) and empty strings to None.

    Args:
        value: The field value to normalize.

    Returns:
        The value, or None if it represents absence.
    """
    if not value or value.lower() == "none":
        return None
    return value

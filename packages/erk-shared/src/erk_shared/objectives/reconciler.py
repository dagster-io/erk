"""Core reconciliation logic for objective auto-advance.

This module determines what action to take for an objective with the `auto-advance`
label by converting LLM inference results into actionable reconciliation decisions.
"""

from erk_shared.objectives.next_step_inference import infer_next_step
from erk_shared.objectives.types import InferenceError, ReconcileAction
from erk_shared.prompt_executor.abc import PromptExecutor


def determine_action(
    executor: PromptExecutor,
    objective_body: str,
) -> ReconcileAction:
    """Determine what reconciliation action to take for an objective.

    Calls infer_next_step() and converts the result to a ReconcileAction.

    Args:
        executor: PromptExecutor for LLM inference
        objective_body: The full markdown body of the objective issue

    Returns:
        ReconcileAction indicating what should be done:
        - action_type="create_plan" with step details if a next step is available
        - action_type="none" if no step is available (all done, blocked, or in progress)
        - action_type="error" if inference failed
    """
    result = infer_next_step(executor, objective_body)

    if isinstance(result, InferenceError):
        return ReconcileAction(
            action_type="error",
            step_id=None,
            step_description=None,
            phase_name=None,
            reason=result.message,
        )

    if result.has_next_step:
        return ReconcileAction(
            action_type="create_plan",
            step_id=result.step_id,
            step_description=result.step_description,
            phase_name=result.phase_name,
            reason=result.reason,
        )

    return ReconcileAction(
        action_type="none",
        step_id=None,
        step_description=None,
        phase_name=None,
        reason=result.reason,
    )

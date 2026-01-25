"""Types for objective step inference.

This module defines the result types for LLM-based inference of the next
actionable step from an objective's roadmap.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NextStepResult:
    """Result of inferring the next actionable step from an objective.

    This represents a successful inference - the LLM was able to analyze
    the objective and determine either the next step or that no step is available.

    Attributes:
        has_next_step: Whether there is an actionable step available.
        step_id: The step identifier (e.g., "1.1", "2A.1"). None if no step.
        step_description: Description of the step. None if no step.
        phase_name: The phase containing this step (e.g., "Phase 1: Roadmap Parser").
            None if no step.
        reason: Explanation of why this step was chosen, or why no step is available.
    """

    has_next_step: bool
    step_id: str | None
    step_description: str | None
    phase_name: str | None
    reason: str


@dataclass(frozen=True)
class InferenceError:
    """Error during LLM inference.

    This represents a failure to complete inference - the LLM call itself failed
    (e.g., rate limited, network error, authentication failure).

    Attributes:
        message: Human-readable error description.
    """

    message: str


@dataclass(frozen=True)
class ReconcileAction:
    """Action determined by the reconciler for an objective.

    Attributes:
        action_type: One of "create_plan", "none", "error"
        step_id: Step ID if action_type is "create_plan", None otherwise
        step_description: Step description if action_type is "create_plan"
        phase_name: Phase name if action_type is "create_plan"
        reason: Human-readable explanation of why this action was chosen
    """

    action_type: str  # "create_plan" | "none" | "error"
    step_id: str | None
    step_description: str | None
    phase_name: str | None
    reason: str


@dataclass(frozen=True)
class ExecuteResult:
    """Result of executing a reconcile action.

    Attributes:
        success: Whether the execution completed successfully
        plan_issue_number: The created plan issue number if successful, None otherwise
        plan_issue_url: The created plan issue URL if successful, None otherwise
        updated_objective_body: The updated objective body if roadmap was updated, None otherwise
        error: Error message if failed, None if successful
    """

    success: bool
    plan_issue_number: int | None
    plan_issue_url: str | None
    updated_objective_body: str | None
    error: str | None

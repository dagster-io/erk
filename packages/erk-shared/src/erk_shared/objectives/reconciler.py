"""Core reconciliation logic for objective auto-advance.

This module determines what action to take for an objective with the `auto-advance`
label by converting LLM inference results into actionable reconciliation decisions.
"""

from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.github.types import BodyText
from erk_shared.objectives.next_step_inference import infer_next_step
from erk_shared.objectives.plan_generator import (
    PlanGenerationError,
    generate_plan_for_step,
)
from erk_shared.objectives.roadmap_updater import update_roadmap_with_plan
from erk_shared.objectives.types import ExecuteResult, InferenceError, ReconcileAction
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


def execute_action(
    action: ReconcileAction,
    *,
    github_issues: GitHubIssues,
    repo_root: Path,
    prompt_executor: PromptExecutor,
    objective_number: int,
    objective_body: str,
) -> ExecuteResult:
    """Execute a reconcile action (create plan, update roadmap).

    For action_type="create_plan":
    1. Generate plan content using generate_plan_for_step()
    2. Create issue using create_plan_issue() with objective_id link
    3. Update objective roadmap to show 'plan #N' in PR column

    For other action types, returns success with no changes.

    Args:
        action: The ReconcileAction to execute
        github_issues: GitHubIssues interface for creating issues
        repo_root: Repository root directory
        prompt_executor: PromptExecutor for LLM plan generation
        objective_number: The objective issue number
        objective_body: The full markdown body of the objective issue

    Returns:
        ExecuteResult with plan issue number on success, error message on failure.
    """
    # Only handle create_plan actions
    if action.action_type != "create_plan":
        return ExecuteResult(
            success=True,
            plan_issue_number=None,
            plan_issue_url=None,
            updated_objective_body=None,
            error=None,
        )

    # Validate required fields are present
    if action.step_id is None or action.step_description is None or action.phase_name is None:
        return ExecuteResult(
            success=False,
            plan_issue_number=None,
            plan_issue_url=None,
            updated_objective_body=None,
            error="ReconcileAction missing required step fields",
        )

    # Step 1: Generate plan content
    plan_result = generate_plan_for_step(
        prompt_executor,
        objective_body=objective_body,
        objective_number=objective_number,
        step_id=action.step_id,
        step_description=action.step_description,
        phase_name=action.phase_name,
    )

    if isinstance(plan_result, PlanGenerationError):
        return ExecuteResult(
            success=False,
            plan_issue_number=None,
            plan_issue_url=None,
            updated_objective_body=None,
            error=f"Plan generation failed: {plan_result.message}",
        )

    # Step 2: Create plan issue with objective_id link
    issue_result = create_plan_issue(
        github_issues,
        repo_root,
        plan_result.content,
        title=plan_result.title,
        extra_labels=None,
        title_tag=None,
        source_repo=None,
        objective_id=objective_number,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=None,
    )

    if not issue_result.success:
        return ExecuteResult(
            success=False,
            plan_issue_number=issue_result.issue_number,  # May be set on partial failure
            plan_issue_url=issue_result.issue_url,
            updated_objective_body=None,
            error=issue_result.error,
        )

    # Step 3: Update objective roadmap with plan reference
    plan_issue_number = issue_result.issue_number
    if plan_issue_number is None:
        return ExecuteResult(
            success=False,
            plan_issue_number=None,
            plan_issue_url=None,
            updated_objective_body=None,
            error="Issue created but no issue number returned",
        )

    update_result = update_roadmap_with_plan(
        objective_body,
        step_id=action.step_id,
        plan_issue_number=plan_issue_number,
    )

    if not update_result.success:
        # Plan was created but roadmap update failed - partial success
        error_msg = (
            f"Plan #{plan_issue_number} created but roadmap update failed: {update_result.error}"
        )
        return ExecuteResult(
            success=False,
            plan_issue_number=plan_issue_number,
            plan_issue_url=issue_result.issue_url,
            updated_objective_body=None,
            error=error_msg,
        )

    # Step 4: Update objective issue body with new roadmap
    if update_result.updated_body is not None:
        github_issues.update_issue_body(
            repo_root,
            objective_number,
            BodyText(content=update_result.updated_body),
        )

    return ExecuteResult(
        success=True,
        plan_issue_number=plan_issue_number,
        plan_issue_url=issue_result.issue_url,
        updated_objective_body=update_result.updated_body,
        error=None,
    )

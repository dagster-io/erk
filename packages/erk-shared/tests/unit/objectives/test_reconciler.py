"""Unit tests for the reconciler module.

Tests cover:
- Converting NextStepResult with has_next_step=True to action_type="create_plan"
- Converting NextStepResult with has_next_step=False to action_type="none"
- Converting InferenceError to action_type="error"
- Verifying objective body is passed through to inference
"""

from erk_shared.objectives.reconciler import determine_action
from erk_shared.prompt_executor.fake import FakePromptExecutor


class TestDetermineAction:
    """Tests for the determine_action function."""

    def test_returns_create_plan_when_next_step_available(self) -> None:
        """Returns create_plan action when inference finds a next step."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: yes
STEP_ID: 2.1
DESCRIPTION: Create ReconcileAction type
PHASE: Phase 2: Reconciler Core
REASON: Phase 1 steps are complete"""
        )

        action = determine_action(fake_executor, "test objective body")

        assert action.action_type == "create_plan"
        assert action.step_id == "2.1"
        assert action.step_description == "Create ReconcileAction type"
        assert action.phase_name == "Phase 2: Reconciler Core"
        assert "Phase 1 steps are complete" in action.reason

    def test_returns_none_when_all_steps_complete(self) -> None:
        """Returns none action when all steps are done."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: All steps are complete"""
        )

        action = determine_action(fake_executor, "test objective body")

        assert action.action_type == "none"
        assert action.step_id is None
        assert action.step_description is None
        assert action.phase_name is None
        assert "All steps are complete" in action.reason

    def test_returns_none_when_all_steps_have_plans(self) -> None:
        """Returns none action when all pending steps have plans in progress."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: All pending steps have plans in progress"""
        )

        action = determine_action(fake_executor, "test objective body")

        assert action.action_type == "none"
        assert action.step_id is None
        assert action.step_description is None
        assert action.phase_name is None
        assert "plans in progress" in action.reason

    def test_returns_error_on_inference_failure(self) -> None:
        """Returns error action when LLM inference fails."""
        fake_executor = FakePromptExecutor(
            should_fail=True,
            error="Rate limited",
        )

        action = determine_action(fake_executor, "test objective body")

        assert action.action_type == "error"
        assert action.step_id is None
        assert action.step_description is None
        assert action.phase_name is None
        assert action.reason == "Rate limited"

    def test_passes_objective_body_to_inference(self) -> None:
        """Verifies the objective body is passed through to inference."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: Test"""
        )

        determine_action(fake_executor, "My custom objective content")

        assert len(fake_executor.prompt_calls) == 1
        assert "My custom objective content" in fake_executor.prompt_calls[0].prompt

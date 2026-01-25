"""Unit tests for the reconciler module.

Tests cover:
- Converting NextStepResult with has_next_step=True to action_type="create_plan"
- Converting NextStepResult with has_next_step=False to action_type="none"
- Converting InferenceError to action_type="error"
- Verifying objective body is passed through to inference
- execute_action() creating plans and updating roadmaps
"""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.objectives.reconciler import determine_action, execute_action
from erk_shared.objectives.types import ReconcileAction
from erk_shared.prompt_executor.fake import FakePromptExecutor


def _create_objective_issue(number: int, body: str) -> IssueInfo:
    """Create an objective issue for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Objective #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective", "auto-advance"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


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


OBJECTIVE_WITH_ROADMAP = """# Test Objective

## Goal

Test objective for reconciler.

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 4.1 | Generate plan content | pending | |
| 4.2 | Create plan issue | pending | |
"""

GENERATED_PLAN_OUTPUT = """# Step 4.1: Generate Plan Content

**Part of Objective #5934, Step 4.1**

## Goal

Generate plan content from objective step.

## Implementation

Do the thing.
"""


class TestExecuteAction:
    """Tests for the execute_action function."""

    def test_execute_action_creates_plan_and_updates_roadmap(self, tmp_path: Path) -> None:
        """Test that execute_action creates plan issue and updates objective roadmap."""
        objective_issue = _create_objective_issue(5934, OBJECTIVE_WITH_ROADMAP)
        issues_ops = FakeGitHubIssues(
            username="testuser",
            labels={"erk-plan"},  # Pre-create label
            next_issue_number=6001,
            issues={5934: objective_issue},  # Pre-register objective
        )

        prompt_executor = FakePromptExecutor(output=GENERATED_PLAN_OUTPUT)

        action = ReconcileAction(
            action_type="create_plan",
            step_id="4.1",
            step_description="Generate plan content",
            phase_name="Phase 4: Plan Generation",
            reason="Previous steps complete",
        )

        result = execute_action(
            action,
            github_issues=issues_ops,
            repo_root=tmp_path,
            prompt_executor=prompt_executor,
            objective_number=5934,
            objective_body=OBJECTIVE_WITH_ROADMAP,
        )

        assert result.success
        assert result.plan_issue_number == 6001
        assert result.error is None

        # Verify plan issue was created
        assert len(issues_ops.created_issues) == 1
        title, body, labels = issues_ops.created_issues[0]
        assert "[erk-plan]" in title
        assert "erk-plan" in labels

        # Verify objective roadmap was updated
        assert result.updated_objective_body is not None
        assert "plan #6001" in result.updated_objective_body

        # Verify objective body was updated in storage
        # Note: 2 updates occur - plan issue (comment_id) and objective (roadmap)
        assert len(issues_ops.updated_bodies) == 2
        # Find the objective update (5934) - it should have the plan reference
        objective_updates = [(num, body) for num, body in issues_ops.updated_bodies if num == 5934]
        assert len(objective_updates) == 1
        updated_body = objective_updates[0][1]
        assert "plan #6001" in updated_body

    def test_execute_action_returns_success_for_none_action(self, tmp_path: Path) -> None:
        """Test that execute_action returns success without changes for none action."""
        issues_ops = FakeGitHubIssues(username="testuser")
        prompt_executor = FakePromptExecutor(output="")

        action = ReconcileAction(
            action_type="none",
            step_id=None,
            step_description=None,
            phase_name=None,
            reason="All steps complete",
        )

        result = execute_action(
            action,
            github_issues=issues_ops,
            repo_root=tmp_path,
            prompt_executor=prompt_executor,
            objective_number=5934,
            objective_body=OBJECTIVE_WITH_ROADMAP,
        )

        assert result.success
        assert result.plan_issue_number is None
        assert result.error is None
        # No issues should have been created
        assert len(issues_ops.created_issues) == 0

    def test_execute_action_returns_error_for_plan_generation_failure(self, tmp_path: Path) -> None:
        """Test that execute_action returns error when plan generation fails."""
        issues_ops = FakeGitHubIssues(username="testuser")
        prompt_executor = FakePromptExecutor(
            should_fail=True,
            error="Rate limited",
        )

        action = ReconcileAction(
            action_type="create_plan",
            step_id="4.1",
            step_description="Generate plan content",
            phase_name="Phase 4",
            reason="Test",
        )

        result = execute_action(
            action,
            github_issues=issues_ops,
            repo_root=tmp_path,
            prompt_executor=prompt_executor,
            objective_number=5934,
            objective_body=OBJECTIVE_WITH_ROADMAP,
        )

        assert not result.success
        assert result.plan_issue_number is None
        assert "Rate limited" in result.error

    def test_execute_action_returns_error_for_missing_step_fields(self, tmp_path: Path) -> None:
        """Test that execute_action returns error when action missing required fields."""
        issues_ops = FakeGitHubIssues(username="testuser")
        prompt_executor = FakePromptExecutor(output="")

        # Action with create_plan type but missing step_id
        action = ReconcileAction(
            action_type="create_plan",
            step_id=None,  # Missing!
            step_description="Generate plan content",
            phase_name="Phase 4",
            reason="Test",
        )

        result = execute_action(
            action,
            github_issues=issues_ops,
            repo_root=tmp_path,
            prompt_executor=prompt_executor,
            objective_number=5934,
            objective_body=OBJECTIVE_WITH_ROADMAP,
        )

        assert not result.success
        assert "missing required step fields" in result.error

    def test_execute_action_handles_roadmap_update_failure(self, tmp_path: Path) -> None:
        """Test that execute_action handles roadmap update failure gracefully."""
        issues_ops = FakeGitHubIssues(
            username="testuser",
            labels={"erk-plan"},
            next_issue_number=6001,
        )

        prompt_executor = FakePromptExecutor(output=GENERATED_PLAN_OUTPUT)

        # Objective without PR column - roadmap update will fail
        objective_without_pr_column = """# Objective

## Roadmap

| Step | Description | Status |
| ---- | ----------- | ------ |
| 4.1 | Generate plan content | pending |
"""

        action = ReconcileAction(
            action_type="create_plan",
            step_id="4.1",
            step_description="Generate plan content",
            phase_name="Phase 4",
            reason="Test",
        )

        result = execute_action(
            action,
            github_issues=issues_ops,
            repo_root=tmp_path,
            prompt_executor=prompt_executor,
            objective_number=5934,
            objective_body=objective_without_pr_column,
        )

        # Plan was created but roadmap update failed
        assert not result.success
        assert result.plan_issue_number == 6001  # Plan was still created
        assert "roadmap update failed" in result.error

    def test_execute_action_links_plan_to_objective(self, tmp_path: Path) -> None:
        """Test that created plan is linked to the objective via objective_id metadata."""
        objective_issue = _create_objective_issue(5934, OBJECTIVE_WITH_ROADMAP)
        issues_ops = FakeGitHubIssues(
            username="testuser",
            labels={"erk-plan"},
            next_issue_number=6001,
            issues={5934: objective_issue},
        )

        prompt_executor = FakePromptExecutor(output=GENERATED_PLAN_OUTPUT)

        action = ReconcileAction(
            action_type="create_plan",
            step_id="4.1",
            step_description="Generate plan content",
            phase_name="Phase 4",
            reason="Test",
        )

        result = execute_action(
            action,
            github_issues=issues_ops,
            repo_root=tmp_path,
            prompt_executor=prompt_executor,
            objective_number=5934,
            objective_body=OBJECTIVE_WITH_ROADMAP,
        )

        assert result.success

        # The plan issue body should contain objective_issue metadata
        # The metadata block is created by create_plan_issue with objective_id parameter
        assert len(issues_ops.created_issues) == 1
        _, body, _ = issues_ops.created_issues[0]
        # The metadata block contains the objective_issue reference
        assert "objective_issue: 5934" in body

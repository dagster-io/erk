"""Tests for objective next-plan --one-shot command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env

OBJECTIVE_BODY = """# Objective: Add caching

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | pending | - | - |
| 1.2 | Add tests | pending | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build feature | pending | - | - |
"""

OBJECTIVE_ALL_DONE_BODY = """# Objective: Done

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
| 1.2 | Add tests | done | - | #101 |
"""

NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


def _make_objective_issue(number: int, body: str) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Add caching",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="testuser",
    )


def _build_one_shot_context(
    env,
    *,
    issues: FakeGitHubIssues,
):
    """Build context for one-shot tests with objective issues."""
    git = FakeGit(
        git_common_dirs={env.cwd: env.git_dir},
        default_branches={env.cwd: "main"},
        trunk_branches={env.cwd: "main"},
        current_branches={env.cwd: "main"},
    )
    github = FakeGitHub(authenticated=True, issues_gateway=issues)

    return build_workspace_test_context(env, git=git, github=github, issues=issues)


def test_next_plan_one_shot_happy_path() -> None:
    """Test --one-shot dispatches workflow with objective/step inputs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Done!" in result.output

        # Verify workflow was triggered with objective/step inputs
        github = ctx.github
        assert isinstance(github, FakeGitHub)
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "one-shot.yml"
        assert inputs["objective_issue"] == "42"
        assert inputs["step_id"] == "1.1"
        assert "Implement step 1.1" in inputs["instruction"]

        # Verify objective body was updated: step 1.1 marked as "planning" with draft PR
        # Note: updated_bodies has 2 entries — one from skeleton plan issue creation
        # (create_plan_issue updates body with comment_id) and one from objective update
        objective_updates = [(num, body) for num, body in issues.updated_bodies if num == 42]
        assert len(objective_updates) == 1
        _, updated_body = objective_updates[0]
        assert "planning" in updated_body.lower() or "planning" in updated_body


def test_next_plan_one_shot_repeated_invocation_advances_step() -> None:
    """Test that running --one-shot twice dispatches different steps.

    After first dispatch marks step 1.1 as 'planning', the second
    invocation should skip it and dispatch step 1.2.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        # First invocation: dispatches step 1.1
        result1 = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot"],
            obj=ctx,
            catch_exceptions=False,
        )
        assert result1.exit_code == 0, f"First invocation failed: {result1.output}"

        github = ctx.github
        assert isinstance(github, FakeGitHub)
        assert len(github.triggered_workflows) == 1
        _, inputs1 = github.triggered_workflows[0]
        assert inputs1["step_id"] == "1.1"

        # Second invocation: should dispatch step 1.2 (since 1.1 is now "planning")
        result2 = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot"],
            obj=ctx,
            catch_exceptions=False,
        )
        assert result2.exit_code == 0, f"Second invocation failed: {result2.output}"

        assert len(github.triggered_workflows) == 2
        _, inputs2 = github.triggered_workflows[1]
        assert inputs2["step_id"] == "1.2"


def test_next_plan_one_shot_auto_detects_next_step() -> None:
    """Test that first pending step is auto-detected."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # First step is done, second is pending
        body = """# Objective: Test

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
| 1.2 | Add tests | pending | - | - |
"""
        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, body)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        github = ctx.github
        assert isinstance(github, FakeGitHub)
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["step_id"] == "1.2"
        assert "Add tests" in inputs["instruction"]


def test_next_plan_one_shot_step_override() -> None:
    """Test --step 2.1 dispatches that specific step."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot", "--step", "2.1"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        github = ctx.github
        assert isinstance(github, FakeGitHub)
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["step_id"] == "2.1"
        assert "Build feature" in inputs["instruction"]


def test_next_plan_one_shot_no_pending_steps() -> None:
    """Test that all-done objective returns cleanly."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_ALL_DONE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "no pending steps" in result.output

        # Verify no workflow was triggered
        github = ctx.github
        assert isinstance(github, FakeGitHub)
        assert len(github.triggered_workflows) == 0


def test_next_plan_one_shot_step_not_found() -> None:
    """Test --step with nonexistent step ID errors."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot", "--step", "99.1"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Step '99.1' not found" in result.output


def test_next_plan_one_shot_dry_run() -> None:
    """Test --dry-run shows info without mutations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot", "--dry-run"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Dry-run mode:" in result.output
        assert "Implement step 1.1" in result.output

        # Verify no mutations occurred
        github = ctx.github
        assert isinstance(github, FakeGitHub)
        assert len(github.triggered_workflows) == 0
        assert len(github.created_prs) == 0
        # No objective body update in dry-run mode
        assert len(issues.updated_bodies) == 0


def test_next_plan_one_shot_objective_not_found() -> None:
    """Test error when objective issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(issues={})
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "999", "--one-shot"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "not found" in result.output


def test_next_plan_one_shot_model_flag() -> None:
    """Test model flag flows through to workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--one-shot", "-m", "opus"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        github = ctx.github
        assert isinstance(github, FakeGitHub)
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["model_name"] == "opus"


def test_next_plan_flags_require_one_shot() -> None:
    """Test --model, --dry-run, --step without --one-shot produce errors."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        issues = FakeGitHubIssues(
            issues={42: _make_objective_issue(42, OBJECTIVE_BODY)},
        )
        ctx = _build_one_shot_context(env, issues=issues)

        # --model without --one-shot
        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "-m", "opus"],
            obj=ctx,
        )
        assert result.exit_code == 1
        assert "--model requires --one-shot" in result.output

        # --dry-run without --one-shot
        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--dry-run"],
            obj=ctx,
        )
        assert result.exit_code == 1
        assert "--dry-run requires --one-shot" in result.output

        # --step without --one-shot
        result = runner.invoke(
            cli,
            ["objective", "next-plan", "42", "--step", "1.1"],
            obj=ctx,
        )
        assert result.exit_code == 1
        assert "--step requires --one-shot" in result.output

"""Tests for erk workflow launch command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.workflow import workflow_group
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_info(
    number: int,
    branch: str,
    state: str,
    title: str | None,
) -> PullRequestInfo:
    """Create a PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=title or f"PR #{number}",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def _make_pr_details(
    number: int,
    *,
    head_ref_name: str,
    state: str,
    base_ref_name: str,
    title: str | None,
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}" if title is None else title,
        body="",
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_workflow_launch_unknown_workflow(tmp_path: Path) -> None:
    """Test error when workflow name is not recognized."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(workflow_group, ["launch", "unknown-workflow"], obj=ctx)

        assert result.exit_code == 2
        assert "Unknown workflow 'unknown-workflow'" in result.output


def test_workflow_launch_pr_fix_conflicts_triggers_workflow(tmp_path: Path) -> None:
    """Test pr-fix-conflicts workflow trigger."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Add feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Add feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(workflow_group, ["launch", "pr-fix-conflicts"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Add feature" in result.output
        assert "Base branch: main" in result.output
        assert "Workflow triggered" in result.output

        # Verify workflow was triggered with correct inputs
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == WORKFLOW_COMMAND_MAP["pr-fix-conflicts"]
        assert inputs["branch_name"] == "feature-branch"
        assert inputs["base_branch"] == "main"
        assert inputs["pr_number"] == "123"
        assert inputs["squash"] == "true"


def test_workflow_launch_pr_fix_conflicts_with_pr_option(tmp_path: Path) -> None:
    """Test pr-fix-conflicts with explicit --pr option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(456, "other-branch", "OPEN", "Other feature")
        pr_details = _make_pr_details(
            number=456,
            head_ref_name="other-branch",
            state="OPEN",
            base_ref_name="main",
            title="Other feature",
        )
        github = FakeGitHub(
            prs={"other-branch": pr_info},
            pr_details={456: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            workflow_group, ["launch", "pr-fix-conflicts", "--pr", "456"], obj=ctx
        )

        assert result.exit_code == 0
        assert "PR #456" in result.output

        # Verify workflow used PR's branch, not current branch
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["branch_name"] == "other-branch"


def test_workflow_launch_pr_fix_conflicts_with_no_squash(tmp_path: Path) -> None:
    """Test pr-fix-conflicts with --no-squash flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            workflow_group, ["launch", "pr-fix-conflicts", "--no-squash"], obj=ctx
        )

        assert result.exit_code == 0

        # Verify squash is false
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["squash"] == "false"


def test_workflow_launch_pr_address_triggers_workflow(tmp_path: Path) -> None:
    """Test pr-address workflow trigger."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Add feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Add feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(workflow_group, ["launch", "pr-address", "--pr", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "PR #123" in result.output
        assert "Workflow triggered" in result.output

        # Verify workflow was triggered
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == WORKFLOW_COMMAND_MAP["pr-address"]
        assert inputs["pr_number"] == "123"


def test_workflow_launch_pr_address_requires_pr_option(tmp_path: Path) -> None:
    """Test pr-address requires --pr option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(workflow_group, ["launch", "pr-address"], obj=ctx)

        assert result.exit_code == 1
        assert "--pr is required for pr-address" in result.output


def test_workflow_launch_objective_reconcile_requires_objective(tmp_path: Path) -> None:
    """Test objective-reconcile workflow requires --objective option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(workflow_group, ["launch", "objective-reconcile"], obj=ctx)

        assert result.exit_code == 1
        assert "--objective is required for objective-reconcile" in result.output


def test_workflow_launch_objective_reconcile_triggers_workflow(tmp_path: Path) -> None:
    """Test objective-reconcile workflow trigger with required --objective."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        github = FakeGitHub()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            workflow_group,
            ["launch", "objective-reconcile", "--objective", "123"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Workflow triggered" in result.output

        # Verify workflow was triggered with objective
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == WORKFLOW_COMMAND_MAP["objective-reconcile"]
        assert inputs["objective"] == "123"
        assert "dry_run" not in inputs


def test_workflow_launch_objective_reconcile_with_dry_run(tmp_path: Path) -> None:
    """Test objective-reconcile with --dry-run option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        github = FakeGitHub()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            workflow_group,
            ["launch", "objective-reconcile", "--objective", "789", "--dry-run"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify options were passed
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["dry_run"] == "true"
        assert inputs["objective"] == "789"


def test_workflow_launch_learn_triggers_workflow(tmp_path: Path) -> None:
    """Test learn workflow trigger."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        github = FakeGitHub()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(workflow_group, ["launch", "learn", "--issue", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "Workflow triggered" in result.output

        # Verify workflow was triggered
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == WORKFLOW_COMMAND_MAP["learn"]
        assert inputs["issue_number"] == "123"


def test_workflow_launch_learn_requires_issue_option(tmp_path: Path) -> None:
    """Test learn requires --issue option."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(workflow_group, ["launch", "learn"], obj=ctx)

        assert result.exit_code == 1
        assert "--issue is required for learn" in result.output


def test_workflow_launch_plan_implement_shows_usage_error(tmp_path: Path) -> None:
    """Test plan-implement suggests using erk plan submit instead."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(
            workflow_group, ["launch", "plan-implement", "--issue", "123"], obj=ctx
        )

        assert result.exit_code == 2
        assert "erk plan submit" in result.output


def test_workflow_launch_with_model_option(tmp_path: Path) -> None:
    """Test --model option is passed to workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(123, "feature-branch", "OPEN", "Feature")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            state="OPEN",
            base_ref_name="main",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "master"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            workflow_group,
            ["launch", "pr-address", "--pr", "123", "--model", "claude-opus-4"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify model is passed
        assert len(github.triggered_workflows) == 1
        _, inputs = github.triggered_workflows[0]
        assert inputs["model_name"] == "claude-opus-4"


def test_workflow_launch_pr_fix_conflicts_closed_pr_fails(tmp_path: Path) -> None:
    """Test error when PR is closed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(111, "closed-branch", "CLOSED", "Closed PR")
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="closed-branch",
            state="CLOSED",
            base_ref_name="main",
            title="Closed PR",
        )
        github = FakeGitHub(
            prs={"closed-branch": pr_info},
            pr_details={111: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "closed-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(workflow_group, ["launch", "pr-fix-conflicts"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot rebase CLOSED PR" in result.output

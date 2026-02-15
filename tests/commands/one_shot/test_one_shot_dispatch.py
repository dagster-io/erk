"""Tests for one-shot dispatch shared logic."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_dispatch_happy_path() -> None:
    """Test dispatch creates skeleton issue, branch with P<N>- prefix, PR, and triggers workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github)

        params = OneShotDispatchParams(
            instruction="fix the import in config.py",
            model=None,
            extra_workflow_inputs={},
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None
        # Branch should have P<N>- prefix (skeleton issue created first)
        assert result.branch_name.startswith("P1-")

        # Verify skeleton plan issue was created
        assert len(issues.created_issues) == 1
        title, _body, labels = issues.created_issues[0]
        assert "[erk-plan]" in title
        assert "erk-plan" in labels

        # Verify branch was created
        assert len(git.created_branches) == 1
        assert git.created_branches[0][2] == "main"  # start_point is trunk

        # Verify push to remote
        assert len(git.pushed_branches) == 1

        # Verify PR was created
        assert len(github.created_prs) == 1
        _branch, _title, _body, base, draft = github.created_prs[0]
        assert draft is True
        assert base == "main"

        # Verify workflow was triggered with plan_issue_number
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "one-shot.yml"
        assert inputs["instruction"] == "fix the import in config.py"
        assert inputs["plan_issue_number"] == "1"

        # Verify we're back on original branch
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_dispatch_with_extra_inputs() -> None:
    """Test extra_workflow_inputs in workflow trigger and skeleton links to objective."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github)

        params = OneShotDispatchParams(
            instruction="implement step 1.1",
            model=None,
            extra_workflow_inputs={
                "objective_issue": "42",
                "step_id": "1.1",
            },
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None
        # Branch should have P<N>- prefix
        assert result.branch_name.startswith("P1-")

        # Verify extra inputs are in workflow trigger
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["objective_issue"] == "42"
        assert inputs["step_id"] == "1.1"
        assert inputs["instruction"] == "implement step 1.1"
        assert inputs["plan_issue_number"] == "1"


def test_dispatch_dry_run() -> None:
    """Test dispatch_one_shot dry_run outputs info without mutations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        # Invoke via CLI to capture user_output via CliRunner
        result = runner.invoke(
            cli,
            ["one-shot", "add type hints", "--dry-run", "-m", "opus"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Dry-run mode:" in result.output
        assert "add type hints" in result.output

        # Verify no mutations occurred (skeleton issue NOT created in dry-run)
        assert len(git.created_branches) == 0
        assert len(git.pushed_branches) == 0
        assert len(github.created_prs) == 0
        assert len(github.triggered_workflows) == 0


def test_dispatch_restores_branch_on_error() -> None:
    """Test that original branch is restored even if push fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            push_to_remote_error=PushError(message="network error"),
        )
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix the import in config.py"],
            obj=ctx,
        )

        # Verify command failed
        assert result.exit_code != 0

        # Verify we're back on original branch despite error
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_dispatch_creates_skeleton_plan_issue() -> None:
    """Test that skeleton plan issue is created with correct content and metadata."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github)

        params = OneShotDispatchParams(
            instruction="add user authentication",
            model=None,
            extra_workflow_inputs={},
        )

        dispatch_one_shot(ctx, params=params, dry_run=False)

        # Verify skeleton issue was created with expected content
        assert len(issues.created_issues) == 1
        title, _body, labels = issues.created_issues[0]
        assert "[erk-plan]" in title
        assert "erk-plan" in labels

        # Verify plan comment was added (create_plan_issue adds plan as comment)
        assert len(issues.added_comments) == 1
        issue_number, comment_body, _comment_id = issues.added_comments[0]
        assert issue_number == 1
        assert "Skeleton" in comment_body
        assert "add user authentication" in comment_body

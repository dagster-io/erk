"""Unit tests for admin test-plan-implement-gh-workflow command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_happy_path_with_existing_issue() -> None:
    """Command succeeds with --issue flag, using existing issue number."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        fake_github = FakeGitHub()
        fake_issues = FakeGitHubIssues()
        ctx = env.build_context(
            current_branch="my-feature",
            github=fake_github,
            issues=fake_issues,
        )

        result = runner.invoke(
            cli, ["admin", "test-plan-implement-gh-workflow", "--issue", "42"], obj=ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify issue 42 was used
        assert "Using existing issue #42" in result.output
        # Verify PR was created as draft
        assert len(fake_github.created_prs) == 1
        branch, title, _body, base, draft = fake_github.created_prs[0]
        assert branch.startswith("test-workflow-")
        assert base == "master"
        assert draft is True
        # Verify workflow was triggered
        assert len(fake_github.triggered_workflows) == 1
        workflow, inputs = fake_github.triggered_workflows[0]
        assert workflow == "plan-implement.yml"
        assert inputs["issue_number"] == "42"
        # Verify output contains run URL
        assert "Workflow triggered successfully" in result.output
        assert "Run URL:" in result.output


def test_happy_path_creating_new_issue() -> None:
    """Command succeeds without --issue, creating a new issue."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        fake_github = FakeGitHub()
        fake_issues = FakeGitHubIssues()
        ctx = env.build_context(
            current_branch="my-feature",
            github=fake_github,
            issues=fake_issues,
        )

        result = runner.invoke(cli, ["admin", "test-plan-implement-gh-workflow"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify issue was created
        assert len(fake_issues.created_issues) == 1
        title, _body, labels = fake_issues.created_issues[0]
        assert title == "Test workflow run"
        assert "test" in labels
        assert "Created test issue #1" in result.output
        # Verify workflow was triggered with the new issue number
        assert len(fake_github.triggered_workflows) == 1
        _, inputs = fake_github.triggered_workflows[0]
        assert inputs["issue_number"] == "1"


def test_error_no_github_remote() -> None:
    """Command fails with clear error when repo has no GitHub remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "my-feature"},
            existing_paths={env.cwd, env.git_dir},
            remote_urls={},
        )
        ctx = env.build_context(git=git)

        result = runner.invoke(cli, ["admin", "test-plan-implement-gh-workflow"], obj=ctx)

        assert result.exit_code == 1
        assert "Not a GitHub repository" in result.output


def test_error_detached_head() -> None:
    """Command fails with clear error when in detached HEAD state."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Don't set current_branch so get_current_branch returns None
        ctx = env.build_context()

        result = runner.invoke(cli, ["admin", "test-plan-implement-gh-workflow"], obj=ctx)

        assert result.exit_code == 1
        assert "detached HEAD" in result.output

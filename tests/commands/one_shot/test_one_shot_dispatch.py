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
    """Test dispatch creates plnd/ branch, draft PR with metadata, and triggers workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="fix the import in config.py",
            model=None,
            extra_workflow_inputs={},
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None
        # Branch uses plnd/ prefix (planned-PR, no skeleton issue)
        assert result.branch_name.startswith("plnd/")

        # No skeleton issue created — draft PR IS the plan
        assert len(issues.created_issues) == 0

        # Verify branch was created
        assert len(git.created_branches) == 1
        assert git.created_branches[0][2] == "main"  # start_point is trunk

        # Verify .erk/impl-context/prompt.md was committed directly to branch (no checkout)
        assert len(git.branch_commits) == 1
        assert git.branch_commits[0].files == {
            ".erk/impl-context/prompt.md": "fix the import in config.py\n",
        }
        assert git.branch_commits[0].branch.startswith("plnd/")

        # Verify push to remote
        assert len(git.pushed_branches) == 1

        # Verify draft PR was created with plan-header metadata block
        assert len(github.created_prs) == 1
        _branch, _title, pr_body, base, draft = github.created_prs[0]
        assert draft is True
        assert base == "main"
        assert "plan-header" in pr_body
        assert "lifecycle_stage: prompted" in pr_body
        assert "fix the import in config.py" in pr_body
        # No Closes #N (self-referential for planned_pr)
        assert "Closes #" not in pr_body

        # erk-plan label added to PR
        pr_number = result.pr_number
        assert (pr_number, "erk-plan") in github.added_labels

        # Verify workflow was triggered with plan_issue_number = pr_number and plan_backend
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "one-shot.yml"
        assert inputs["prompt"] == "fix the import in config.py"
        assert inputs["plan_issue_number"] == str(pr_number)
        assert inputs["plan_backend"] == "planned_pr"

        # Verify PR body was updated (at minimum: footer update)
        assert len(github.updated_pr_bodies) >= 1

        # Verify we're back on original branch
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_dispatch_with_extra_inputs() -> None:
    """Test extra_workflow_inputs in workflow trigger with objective linking."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="implement step 1.1",
            model=None,
            extra_workflow_inputs={
                "objective_issue": "42",
                "node_id": "1.1",
            },
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None
        # Branch uses plnd/ prefix
        assert result.branch_name.startswith("plnd/")

        # Verify extra inputs are in workflow trigger
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["objective_issue"] == "42"
        assert inputs["node_id"] == "1.1"
        assert inputs["prompt"] == "implement step 1.1"
        assert inputs["plan_issue_number"] == str(result.pr_number)


def test_dispatch_dry_run() -> None:
    """Test dispatch_one_shot dry_run outputs info without mutations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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


def test_dispatch_stays_on_current_branch_on_error() -> None:
    """Test that we stay on current branch when push fails (no checkout = nothing to restore)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
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

        # Verify we're still on original branch (no checkout occurred)
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_dispatch_long_prompt_truncates_workflow_input() -> None:
    """Test that long prompts are truncated in workflow input but committed in full."""
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

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        long_prompt = "x" * 1000

        params = OneShotDispatchParams(
            prompt=long_prompt,
            model=None,
            extra_workflow_inputs={},
        )

        result = dispatch_one_shot(ctx, params=params, dry_run=False)

        assert result is not None

        # Verify workflow input was truncated
        _workflow, inputs = github.triggered_workflows[0]
        assert len(inputs["prompt"]) < len(long_prompt)
        assert inputs["prompt"].endswith(
            "... (full prompt committed to .erk/impl-context/prompt.md)"
        )

        # Verify full prompt was committed directly to branch via branch_commits
        assert len(git.branch_commits) == 1
        assert git.branch_commits[0].files == {".erk/impl-context/prompt.md": long_prompt + "\n"}

"""Tests for erk pr prepare command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.github.types import PRDetails
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    number: int,
    head_ref_name: str,
    *,
    body: str = "## Plan\nTest plan content",
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}",
        body=body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_prepare_auto_detects_plan_from_branch() -> None:
    """Test pr prepare auto-detects plan number from current branch's PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(number=200, head_ref_name="feature-branch")
        github = FakeLocalGitHub(
            pr_details={200: pr_details},
            prs_by_branch={"feature-branch": pr_details},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["prepare"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Prepared impl-context for plan #200" in result.output


def test_prepare_with_explicit_plan_number() -> None:
    """Test pr prepare with explicit plan number argument."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(number=300, head_ref_name="other-branch")
        github = FakeLocalGitHub(pr_details={300: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "my-feature"},
            local_branches={env.cwd: ["main", "my-feature"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["prepare", "300"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Prepared impl-context for plan #300" in result.output


def test_prepare_error_no_pr_for_branch() -> None:
    """Test pr prepare errors when no PR found for current branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        github = FakeLocalGitHub()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "orphan-branch"},
            local_branches={env.cwd: ["main", "orphan-branch"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["prepare"], obj=ctx)

        assert result.exit_code == 1
        assert "No PR found for branch" in result.output


def test_prepare_idempotent_existing_impl_context() -> None:
    """Test pr prepare is idempotent when impl-context already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(number=400, head_ref_name="feature-branch")
        github = FakeLocalGitHub(
            pr_details={400: pr_details},
            prs_by_branch={"feature-branch": pr_details},
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # First invocation: creates impl-context
        result1 = runner.invoke(pr_group, ["prepare"], obj=ctx)
        assert result1.exit_code == 0, result1.output
        assert "Prepared impl-context for plan #400" in result1.output

        # Second invocation: idempotent
        result2 = runner.invoke(pr_group, ["prepare"], obj=ctx)
        assert result2.exit_code == 0, result2.output
        assert "already set up" in result2.output

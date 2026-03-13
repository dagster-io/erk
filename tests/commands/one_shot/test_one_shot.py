"""Tests for erk one-shot command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_remote() -> FakeRemoteGitHub:
    """Create a default FakeRemoteGitHub for tests."""
    return FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
    )


def test_one_shot_happy_path() -> None:
    """Test one-shot command creates branch, PR, and triggers workflow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["one-shot", "fix the import in config.py"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Done!" in result.output

        # Verify branch was created via RemoteGitHub
        assert len(remote.created_refs) == 1
        ref = remote.created_refs[0]
        assert ref.ref.startswith("refs/heads/plnd/")

        # Verify prompt was committed
        assert len(remote.created_file_commits) == 1
        assert "fix the import in config.py" in remote.created_file_commits[0].content

        # Verify PR was created as draft
        assert len(remote.created_pull_requests) == 1
        pr = remote.created_pull_requests[0]
        assert pr.draft is True
        assert "One-shot:" in pr.title
        assert pr.base == "main"

        # Verify workflow was triggered
        assert len(remote.dispatched_workflows) == 1
        wf = remote.dispatched_workflows[0]
        assert wf.workflow == "one-shot.yml"
        assert wf.inputs["prompt"] == "fix the import in config.py"


def test_one_shot_empty_prompt() -> None:
    """Test that empty prompt is rejected."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "   "],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Prompt must not be empty" in result.output


def test_one_shot_dry_run() -> None:
    """Test dry-run mode shows what would happen without executing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["one-shot", "add type hints", "--dry-run"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Dry-run mode:" in result.output
        assert "add type hints" in result.output

        # Verify no mutations occurred
        assert len(remote.created_refs) == 0
        assert len(remote.created_pull_requests) == 0
        assert len(remote.dispatched_workflows) == 0


def test_one_shot_with_model() -> None:
    """Test model flag is passed to workflow inputs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "-m", "opus"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify model was passed to workflow
        assert len(remote.dispatched_workflows) == 1
        assert remote.dispatched_workflows[0].inputs["model_name"] == "opus"


def test_one_shot_model_alias() -> None:
    """Test model alias expansion (o -> opus)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "-m", "o"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert remote.dispatched_workflows[0].inputs["model_name"] == "opus"


def test_one_shot_pr_title_truncation() -> None:
    """Test that long prompts are truncated in PR title."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        long_prompt = "a" * 100

        result = runner.invoke(
            cli,
            ["one-shot", long_prompt],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # PR title should be truncated
        pr = remote.created_pull_requests[0]
        assert "..." in pr.title
        assert len(pr.title) < len(long_prompt) + 20


def test_one_shot_file_option() -> None:
    """Test --file option reads prompt from a file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Write prompt to a file
        prompt_file = env.cwd / "prompt.md"
        prompt_file.write_text("fix the import in config.py\n", encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["one-shot", "--file", str(prompt_file)],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Done!" in result.output

        # Verify prompt was read from file and passed through
        assert len(remote.dispatched_workflows) == 1
        assert "fix the import in config.py" in remote.dispatched_workflows[0].inputs["prompt"]


def test_one_shot_file_and_argument_rejected() -> None:
    """Test that providing both --file and argument is rejected."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        prompt_file = env.cwd / "prompt.md"
        prompt_file.write_text("some prompt\n", encoding="utf-8")

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "inline prompt", "--file", str(prompt_file)],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "not both" in result.output


def test_one_shot_plan_only_flag() -> None:
    """Test --plan-only flag is passed through to workflow inputs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["one-shot", "create a plan for refactoring", "--plan-only"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify plan_only was passed to workflow inputs
        assert len(remote.dispatched_workflows) == 1
        assert remote.dispatched_workflows[0].inputs["plan_only"] == "true"


def test_one_shot_no_prompt_rejected() -> None:
    """Test that providing neither argument nor --file is rejected."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "prompt argument or --file" in result.output

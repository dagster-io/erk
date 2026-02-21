"""Tests for erk one-shot command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.fake import FakeGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix the import in config.py"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Done!" in result.output

        # Verify branch was created with P<N>- prefix (skeleton plan issue created first)
        assert len(git.created_branches) == 1
        created = git.created_branches[0]
        assert created[1].startswith("P")
        assert created[2] == "main"  # start_point is trunk

        # Verify push to remote
        assert len(git.pushed_branches) == 1
        push = git.pushed_branches[0]
        assert push.remote == "origin"
        assert push.set_upstream is True

        # Verify commit was made
        assert len(git.commits) == 1
        assert "fix the import in config.py" in git.commits[0].message

        # Verify PR was created: tuple is (branch, title, body, base, draft)
        assert len(github.created_prs) == 1
        branch, title, body, base, draft = github.created_prs[0]
        assert draft is True
        assert "One-shot:" in title
        assert base == "main"

        # Verify workflow was triggered: tuple is (workflow, inputs)
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "one-shot.yml"
        assert inputs["prompt"] == "fix the import in config.py"
        assert "branch_name" in inputs
        assert "pr_number" in inputs

        # Verify we're back on original branch
        assert git.branch.get_current_branch(env.cwd) == "main"


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
        github = FakeGitHub(authenticated=True)

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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "add type hints", "--dry-run"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Dry-run mode:" in result.output
        assert "add type hints" in result.output
        assert "oneshot-" in result.output
        assert "main" in result.output

        # Verify no mutations occurred
        assert len(git.created_branches) == 0
        assert len(git.pushed_branches) == 0
        assert len(github.created_prs) == 0
        assert len(github.triggered_workflows) == 0


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "-m", "opus"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify model was passed to workflow: tuple is (workflow, inputs)
        assert len(github.triggered_workflows) == 1
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["model_name"] == "opus"


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "-m", "o"],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        _workflow, inputs = github.triggered_workflows[0]
        assert inputs["model_name"] == "opus"


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        long_prompt = "a" * 100

        result = runner.invoke(
            cli,
            ["one-shot", long_prompt],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # PR title should be truncated: tuple is (branch, title, body, base, draft)
        _branch, title, _body, _base, _draft = github.created_prs[0]
        assert "..." in title
        assert len(title) < len(long_prompt) + 20


def test_one_shot_restores_branch_on_error() -> None:
    """Test that original branch is restored even if push fails."""
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

        # Verify we're back on original branch despite error
        assert git.branch.get_current_branch(env.cwd) == "main"


def test_one_shot_rejects_detached_head() -> None:
    """Test that one-shot rejects execution from detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: None},
        )
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix something"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "detached HEAD" in result.output
        assert len(git.created_branches) == 0


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "--file", str(prompt_file)],
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Done!" in result.output

        # Verify prompt was read from file and passed through
        assert len(github.triggered_workflows) == 1
        _workflow, inputs = github.triggered_workflows[0]
        assert "fix the import in config.py" in inputs["prompt"]


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "inline prompt", "--file", str(prompt_file)],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "not both" in result.output


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
        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "prompt argument or --file" in result.output

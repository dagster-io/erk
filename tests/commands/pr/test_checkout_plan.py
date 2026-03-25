"""Tests for plan checkout via pr checkout command (P-prefix routing)."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.github_parsing import parse_issue_identifier
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env

# ============================================================================
# Tests for parse_issue_identifier P-prefix support
# ============================================================================


def test_parse_issue_identifier_p_prefix_uppercase() -> None:
    """Test parsing P-prefixed identifier with uppercase P."""
    result = parse_issue_identifier("P123")
    assert result == 123


def test_parse_issue_identifier_p_prefix_lowercase() -> None:
    """Test parsing P-prefixed identifier with lowercase p."""
    result = parse_issue_identifier("p456")
    assert result == 456


def test_parse_issue_identifier_p_prefix_large_number() -> None:
    """Test parsing P-prefixed identifier with large number."""
    result = parse_issue_identifier("P12345")
    assert result == 12345


def test_parse_issue_identifier_plain_number_still_works() -> None:
    """Test that plain numbers still parse correctly."""
    result = parse_issue_identifier("789")
    assert result == 789


# ============================================================================
# Tests for plan checkout error behavior (P-prefix now unsupported)
# ============================================================================


def test_checkout_p_prefix_shows_error() -> None:
    """Test checkout with P-prefix shows error message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(cli, ["pr", "checkout", "P123"], obj=ctx)

        assert result.exit_code == 1
        assert "Plan checkout is not supported" in result.output


def test_checkout_issue_url_shows_error() -> None:
    """Test checkout with GitHub issue URL shows error message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(
            cli,
            ["pr", "checkout", "https://github.com/owner/repo/issues/555"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Plan checkout is not supported" in result.output


def test_checkout_invalid_identifier() -> None:
    """Test checkout with invalid identifier shows error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(cli, ["pr", "checkout", "invalid-input"], obj=ctx)

        assert result.exit_code != 0
        assert "Invalid PR number" in result.output

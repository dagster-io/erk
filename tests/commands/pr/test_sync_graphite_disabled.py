"""Tests for pr sync command with Graphite disabled.

This file verifies that pr sync shows proper error messages when Graphite
is disabled (use_graphite=False). Unlike other commands that work without
Graphite, pr sync REQUIRES Graphite and should show a helpful error.
"""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_sync_shows_error_when_graphite_config_disabled() -> None:
    """pr sync shows helpful error when Graphite is disabled via config.

    When use_graphite=False in config, the command should fail with a message
    explaining how to enable Graphite.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # GraphiteDisabled sentinel with CONFIG_DISABLED reason
        graphite = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=FakeGitHub(authenticated=True),
            graphite=graphite,
            claude_executor=FakeClaudeExecutor(claude_available=True),
            use_graphite=False,  # Explicitly disabled
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Should fail with helpful error
        assert result.exit_code != 0
        assert "requires Graphite" in result.output or "Graphite" in result.output
        # Should suggest how to enable
        assert "use_graphite" in result.output or "enable" in result.output.lower()


def test_pr_sync_shows_error_when_graphite_not_installed() -> None:
    """pr sync shows helpful error when Graphite is not installed.

    When Graphite is not installed (NOT_INSTALLED reason), the command
    should fail with a message explaining how to install it.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # GraphiteDisabled sentinel with NOT_INSTALLED reason
        graphite = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=FakeGitHub(authenticated=True),
            graphite=graphite,
            claude_executor=FakeClaudeExecutor(claude_available=True),
            use_graphite=False,
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Should fail with helpful error
        assert result.exit_code != 0
        assert "Graphite" in result.output
        # Should suggest installation
        assert "install" in result.output.lower() or "npm" in result.output


def test_pr_sync_error_message_is_user_friendly() -> None:
    """pr sync error message is clear and actionable for users."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=FakeGitHub(authenticated=True),
            graphite=graphite,
            claude_executor=FakeClaudeExecutor(claude_available=True),
            use_graphite=False,
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Should not show internal exception names
        assert "GraphiteDisabledError" not in result.output
        # Should not show stack traces
        assert "Traceback" not in result.output
        # Error should be formatted nicely
        assert result.exit_code != 0


def test_pr_sync_fails_before_any_mutations_when_graphite_disabled() -> None:
    """pr sync fails early (before any mutations) when Graphite is disabled.

    The Ensure.graphite_available() check should happen before any
    API calls or git operations to prevent partial state.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        github = FakeGitHub(authenticated=True)
        graphite = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=FakeClaudeExecutor(claude_available=True),
            use_graphite=False,
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Should fail
        assert result.exit_code != 0
        # Should not have made any git mutations (early failure)
        assert len(git._commits) == 0
        assert len(git._pushed_branches) == 0

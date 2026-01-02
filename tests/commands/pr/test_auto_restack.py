"""Tests for erk pr auto-restack command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_auto_restack_success() -> None:
    """Test successful auto-restack via fast path (no conflicts)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=False,  # No conflicts
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Fast path: Claude should NOT be invoked (no conflicts)
        assert len(claude_executor.executed_commands) == 0

        # Graphite restack should have been called
        assert len(graphite.restack_calls) == 1


def test_pr_auto_restack_requires_dangerous_flag() -> None:
    """Test that command fails when --dangerous flag is not provided (default config)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        assert result.exit_code != 0
        assert "Missing option '--dangerous'" in result.output
        # Verify error message includes config hint
        assert "auto_restack_require_dangerous_flag false" in result.output


def test_pr_auto_restack_skip_dangerous_with_config() -> None:
    """Test that --dangerous flag is not required when config disables requirement."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=False,  # No conflicts
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Create GlobalConfig with auto_restack_require_dangerous_flag=False
        from erk_shared.context.types import GlobalConfig

        global_config = GlobalConfig.test(
            env.erk_root,
            auto_restack_require_dangerous_flag=False,  # Disable --dangerous requirement
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
            global_config=global_config,
        )

        # Invoke WITHOUT --dangerous flag
        result = runner.invoke(pr_group, ["auto-restack"], obj=ctx)

        # Should succeed without --dangerous when config disables requirement
        assert result.exit_code == 0
        assert "Restack complete!" in result.output


def test_pr_auto_restack_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available and conflicts exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        assert "Conflicts require Claude" in result.output
        assert "claude.com/download" in result.output

        # Verify no command was executed
        assert len(claude_executor.executed_commands) == 0


def test_pr_auto_restack_fails_on_command_error() -> None:
    """Test that command fails when slash command execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        assert result.exit_code != 0
        # Error message from FakeClaudeExecutor
        assert "failed" in result.output.lower()


def test_pr_auto_restack_aborts_on_semantic_conflict() -> None:
    """Test that command aborts when Claude prompts for user input (semantic conflict)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        # Simulate Claude using AskUserQuestion tool (semantic conflict)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_tool_events=["Using AskUserQuestion..."],
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        # Should fail with semantic conflict message
        assert result.exit_code != 0
        assert "Semantic conflict detected" in result.output
        assert "interactive resolution" in result.output
        assert "claude /erk:auto-restack" in result.output


def test_pr_auto_restack_fallback_on_conflicts() -> None:
    """Test fallback: conflicts detected, Claude IS invoked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Single commit, no squash needed
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        # Claude handles it, so should succeed
        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Fallback path: Claude SHOULD be invoked
        assert len(claude_executor.executed_commands) == 1
        command, _, dangerous_flag, _ = claude_executor.executed_commands[0]
        assert command == "/erk:auto-restack"
        assert dangerous_flag is True


def test_pr_auto_restack_fast_path_with_rebase_in_progress_but_no_conflicts() -> None:
    """Test fast path: rebase in progress but no actual conflicts (rebase_continue clears state)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Rebase in progress...
            conflicted_files=[],  # ...but NO actual conflicts
            rebase_continue_clears_rebase=True,  # rebase_continue will complete the rebase
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "Restack complete!" in result.output

        # Fast path: Claude should NOT be invoked (no actual conflicts)
        assert len(claude_executor.executed_commands) == 0

        # rebase_continue should have been called to clear the rebase state
        assert len(git.rebase_continue_calls) == 1


def test_pr_auto_restack_preflight_error() -> None:
    """Test preflight error: error reported, Claude NOT invoked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 0},  # No commits - this should error
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        # Preflight error
        assert result.exit_code != 0
        assert "No commits found" in result.output

        # Preflight error: Claude should NOT be invoked
        assert len(claude_executor.executed_commands) == 0


def test_pr_auto_restack_auto_commits_dirty_working_tree() -> None:
    """Test that command auto-commits when working tree has uncommitted changes."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            dirty_worktrees={env.cwd},  # Working tree has uncommitted changes
            rebase_in_progress=False,  # No conflicts
        )

        graphite = FakeGraphite()
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        # Should succeed after auto-committing
        assert result.exit_code == 0
        assert "Auto-committing" in result.output

        # A commit should have been created with the WIP message
        assert len(git.commits) >= 1
        commit_messages = [msg for _, msg, _ in git.commits]
        assert "WIP: auto-commit before restack" in commit_messages

        # Graphite restack should have been called (we proceed after auto-commit)
        assert len(graphite.restack_calls) == 1


def test_pr_auto_restack_fails_when_no_work_events() -> None:
    """Test that command fails when Claude completes but produces no work events."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to restack
            rebase_in_progress=True,  # Conflicts detected
            conflicted_files=["src/file.py"],
        )

        graphite = FakeGraphite()
        # Simulate Claude completing but emitting no work events
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_no_work_events=True,
        )

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        # Should fail due to no work events
        assert result.exit_code != 0
        assert "without producing any output" in result.output
        assert "check hooks" in result.output


def test_pr_auto_restack_graphite_not_enabled() -> None:
    """Test pr auto-restack command requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        # Graphite is NOT enabled - use GraphiteDisabled sentinel
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite_disabled, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.output
        assert "erk config set use_graphite true" in result.output


def test_pr_auto_restack_graphite_not_installed() -> None:
    """Test pr auto-restack command shows appropriate error when Graphite CLI is not installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        # Graphite not installed - use GraphiteDisabled with NOT_INSTALLED reason
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, graphite=graphite_disabled, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["auto-restack", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "requires Graphite to be installed" in result.output
        assert "npm install -g @withgraphite/graphite-cli" in result.output

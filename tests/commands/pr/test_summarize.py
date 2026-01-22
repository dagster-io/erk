"""Tests for erk pr summarize command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_summarize_fails_when_claude_not_available() -> None:
    """Test error when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        # Claude not available
        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 1
        assert "Claude CLI not found" in result.output


def test_summarize_fails_when_detached_head() -> None:
    """Test error when on detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},  # Detached HEAD
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 1
        assert "detached HEAD" in result.output


def test_summarize_fails_when_no_commits() -> None:
    """Test error when branch has no commits ahead of parent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 0},  # No commits ahead
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 1
        assert "No commits to summarize" in result.output
        assert "Make a commit first" in result.output


def test_summarize_fails_when_multiple_commits() -> None:
    """Test error when branch has multiple commits (needs gt squash)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 3},  # Multiple commits
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 1
        assert "Found 3 commits on branch" in result.output
        assert "gt squash" in result.output


def test_summarize_success_with_single_commit() -> None:
    """Test successful summarize with single commit."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 1},  # Single commit
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+new line"},
        )

        # Configure Claude executor with generated message
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output=(
                "Add new feature to file.py\n\n"
                "This commit adds a new line to improve functionality."
            ),
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "1 commit found" in result.output
        assert "Commit amended" in result.output
        assert "Done!" in result.output
        assert "Title: Add new feature to file.py" in result.output


def test_summarize_uses_graphite_parent_branch() -> None:
    """Test that summarize uses Graphite parent branch when available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Set up Graphite-tracked branch
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "child-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={
                (env.cwd, "parent-branch"): 1,  # 1 commit from graphite parent
            },
            diff_to_branch={(env.cwd, "parent-branch"): "diff --git a/file.py b/file.py\n+change"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Test Title\n\nTest body",
        )

        # Configure FakeGraphite with branch metadata showing parent relationship
        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["parent-branch"]),
                "parent-branch": BranchMetadata.branch(
                    "parent-branch", "main", children=["child-branch"]
                ),
                "child-branch": BranchMetadata.branch("child-branch", "parent-branch"),
            }
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            claude_executor=claude_executor,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(pr_group, ["summarize", "--debug"], obj=ctx)

        assert result.exit_code == 0
        assert "Parent: parent-branch" in result.output


def test_summarize_amends_commit_with_generated_message() -> None:
    """Test that summarize calls amend_commit with the generated message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/test.py b/test.py\n+code"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Implement feature X\n\nDetailed description of the changes.",
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0

        # Check that amend was called by verifying the commit was tracked
        # FakeGit tracks commits via self._commits
        assert len(git._commits) == 1
        _, message, _ = git._commits[0]
        assert "Implement feature X" in message
        assert "Detailed description of the changes." in message


def test_summarize_fails_when_message_generation_fails() -> None:
    """Test error handling when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/test.py b/test.py\n+code"},
        )

        # Configure Claude to fail
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="API rate limit exceeded",
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 1
        assert "Failed to generate message" in result.output


def test_summarize_handles_title_only_response() -> None:
    """Test handling when Claude returns only a title with no body."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/test.py b/test.py\n+code"},
        )

        # Claude returns title only (no body)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Fix typo in documentation",
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "Title: Fix typo in documentation" in result.output
        # Should not show "Body:" since there's no body
        assert "Body:" not in result.output


def test_summarize_debug_shows_branch_info() -> None:
    """Test that --debug flag shows additional branch information."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "my-feature"},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/test.py b/test.py\n+code"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Test commit message",
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize", "--debug"], obj=ctx)

        assert result.exit_code == 0
        assert "Branch: my-feature" in result.output
        assert "Parent: main" in result.output

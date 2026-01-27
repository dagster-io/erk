"""Tests for erk pr summarize command.

These tests verify the CLI layer behavior of the summarize command.
The command generates an AI-powered commit message and amends the current commit.
"""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_summarize_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output


def test_pr_summarize_fails_when_no_commits_ahead() -> None:
    """Test that command fails when branch has no commits ahead of parent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 0},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "No commits ahead" in result.output
        assert "Make a commit first" in result.output


def test_pr_summarize_fails_when_multiple_commits() -> None:
    """Test that command fails when multiple commits exist (needs squash)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 3},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "Multiple commits (3)" in result.output
        assert "gt squash" in result.output


def test_pr_summarize_success_amends_commit() -> None:
    """Test successful summarize generates message and amends commit."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+new content"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        github = FakeGitHub(authenticated=True)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add awesome feature\n\nThis PR adds an awesome new feature.",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0
        assert "Commit message updated" in result.output
        assert "Add awesome feature" in result.output

        # Verify commit was amended (amend_commit adds or updates in git.commits)
        assert len(git.commits) == 1
        commit_message = git.commits[0].message
        assert "Add awesome feature" in commit_message
        assert "awesome new feature" in commit_message


def test_pr_summarize_uses_graphite_parent() -> None:
    """Test that summarize uses Graphite parent branch, not trunk.

    Stack: main (trunk) → branch-1 → branch-2 (current)
    Expected: Diff computed against branch-1, not main
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "branch-1", "branch-2"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "branch-2"},
            commits_ahead={(env.cwd, "branch-1"): 1},
            diff_to_branch={(env.cwd, "branch-1"): "diff --git a/file2.py b/file2.py\n+feature 2"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "branch-2": BranchMetadata(
                    name="branch-2",
                    parent="branch-1",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "branch-1": BranchMetadata(
                    name="branch-1",
                    parent="main",
                    children=["branch-2"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["branch-1"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )
        github = FakeGitHub(authenticated=True)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature 2\n\nThis adds feature 2.",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code == 0

        # Verify the prompt was called with correct branches
        assert len(claude_executor.prompt_calls) == 1
        prompt, system_prompt = claude_executor.prompt_calls[0]
        # Should contain branch-1 as parent (Graphite parent)
        assert "branch-1" in prompt
        assert "branch-2" in prompt


def test_pr_summarize_fails_when_message_generation_fails() -> None:
    """Test that command fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+content"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="Claude CLI execution failed",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["summarize"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output

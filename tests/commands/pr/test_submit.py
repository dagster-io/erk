"""Tests for erk pr submit command.

These tests verify the CLI layer behavior of the submit command.
The command now uses Python orchestration with two-layer architecture:
- Core layer: git push + gh pr create (via execute_core_submit)
- Graphite layer: Optional enhancement (via execute_graphite_enhance)
"""

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.cli.commands.pr import pr_group
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_submit_fails_when_claude_not_available() -> None:
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

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output


def test_pr_submit_fails_when_core_submit_returns_error() -> None:
    """Test that command fails when core submit returns error (GitHub not authenticated)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.cwd},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 2},
        )

        # GitHub not authenticated - will cause execute_core_submit to fail
        github = FakeGitHub(authenticated=False)

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "not authenticated" in result.output


def test_pr_submit_fails_when_commit_message_generation_fails() -> None:
    """Test that command fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.cwd},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 2},
            remote_urls={(env.cwd, "origin"): "git@github.com:owner/repo.git"},
        )

        # Configure GitHub with pr_diffs so diff extraction succeeds
        # FakeGitHub.create_pr returns 999 by default
        github = FakeGitHub(
            authenticated=True,
            pr_diffs={999: "diff --git a/file.py b/file.py\n+new line"},
        )

        # Configure executor to fail on prompt
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="Claude CLI execution failed",
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output


def test_pr_submit_fails_when_finalize_fails() -> None:
    """Test that command fails when finalize returns an error (PR update fails)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.cwd},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 2},
            remote_urls={(env.cwd, "origin"): "git@github.com:owner/repo.git"},
        )

        # Configure GitHub to fail PR updates
        github = FakeGitHub(
            authenticated=True,
            pr_diffs={999: "diff content"},
            pr_update_should_succeed=False,  # Finalize will fail
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature\n\nThis adds a new feature.",
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        # The exact error comes from the RuntimeError raised by FakeGitHub
        assert "configured to fail" in result.output or result.exit_code != 0


def test_pr_submit_success() -> None:
    """Test successful PR submission with all phases completing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.cwd},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 2},
            remote_urls={(env.cwd, "origin"): "git@github.com:owner/repo.git"},
        )

        # Configure full success path
        github = FakeGitHub(
            authenticated=True,
            pr_diffs={999: "diff --git a/file.py b/file.py\n+awesome feature"},
        )

        graphite = FakeGraphite(authenticated=True)  # Not tracked, will skip

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

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0

        # Verify PR was created (initially with WIP title)
        assert len(github.created_prs) == 1
        branch, title, _body, base, _draft = github.created_prs[0]
        assert branch == "feature"
        assert title == "WIP"  # Initial title before AI generation
        assert base == "main"

        # Verify PR title was updated after AI generation
        assert len(github.updated_pr_titles) == 1
        pr_number, updated_title = github.updated_pr_titles[0]
        assert pr_number == 999
        assert updated_title == "Add awesome feature"

        # Verify Claude was called
        assert len(claude_executor.prompt_calls) == 1
        prompt = claude_executor.prompt_calls[0]
        assert "feature" in prompt  # Branch name in context
        assert "main" in prompt  # Parent branch in context

        # Verify git push was called
        assert len(git._pushed_branches) == 1
        remote, branch_pushed, set_upstream = git._pushed_branches[0]
        assert remote == "origin"
        assert branch_pushed == "feature"
        assert set_upstream is True


def test_pr_submit_with_no_graphite_flag() -> None:
    """Test that --no-graphite flag skips Graphite enhancement."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.cwd},
            trunk_branches={env.cwd: "main"},
            commits_ahead={(env.cwd, "main"): 2},
            remote_urls={(env.cwd, "origin"): "git@github.com:owner/repo.git"},
        )

        github = FakeGitHub(
            authenticated=True,
            pr_diffs={999: "diff content"},
        )

        graphite = FakeGraphite(authenticated=True)

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Title\n\nBody",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["submit", "--no-graphite"], obj=ctx)

        assert result.exit_code == 0

        # Verify Graphite submit stack was NOT called (flag disabled it)
        assert len(graphite.submit_stack_calls) == 0

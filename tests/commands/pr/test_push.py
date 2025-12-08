"""Tests for erk pr push command.

These tests verify the CLI layer behavior of the push command.
The command uses Python orchestration (preflight -> generate -> finalize)
for git-only PR workflows without Graphite.

Tests use fake implementations instead of mocks for testability.
"""

import subprocess

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails

from erk.cli.commands.pr import pr_group
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_push_fails_when_claude_not_available() -> None:
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

        result = runner.invoke(pr_group, ["push"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output


def test_pr_push_fails_when_github_not_authenticated() -> None:
    """Test that command fails when GitHub CLI is not authenticated."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            trunk_branches={env.cwd: "main"},
            repository_roots={env.cwd: env.cwd},
        )

        github = FakeGitHub(authenticated=False)
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["push"], obj=ctx)

        assert result.exit_code != 0
        assert "not authenticated" in result.output


def test_pr_push_fails_when_push_fails() -> None:
    """Test that command fails when push to remote fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            trunk_branches={env.cwd: "main"},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},  # Clean working tree
            commit_messages_since={(env.cwd, "main"): ["Initial commit"]},
            push_to_remote_raises=subprocess.CalledProcessError(
                returncode=1, cmd=["git", "push"], stderr="rejected"
            ),
        )

        github = FakeGitHub(authenticated=True)
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["push"], obj=ctx)

        assert result.exit_code != 0
        assert "push" in result.output.lower() or "Failed" in result.output


def test_pr_push_fails_when_commit_message_generation_fails() -> None:
    """Test that command fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            trunk_branches={env.cwd: "main"},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},  # Clean working tree
            commit_messages_since={(env.cwd, "main"): ["Initial commit"]},
        )

        # Configure GitHub with existing PR
        pr_info = PullRequestInfoBuilder(123, "feature").build()
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={
                123: PRDetails(
                    number=123,
                    title="Feature",
                    url="https://github.com/org/repo/pull/123",
                    state="OPEN",
                    body="",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="org",
                    repo="repo",
                )
            },
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new line"},
        )

        # Configure executor to fail on prompt
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="Claude CLI execution failed",
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["push"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output


def test_pr_push_fails_when_pr_update_fails() -> None:
    """Test that command fails when PR metadata update fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            trunk_branches={env.cwd: "main"},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},  # Clean working tree
            commit_messages_since={(env.cwd, "main"): ["Initial commit"]},
        )

        # Configure GitHub with existing PR but failing update
        pr_info = PullRequestInfoBuilder(123, "feature").build()
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={
                123: PRDetails(
                    number=123,
                    title="Feature",
                    url="https://github.com/org/repo/pull/123",
                    state="OPEN",
                    body="",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="org",
                    repo="repo",
                )
            },
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new line"},
            pr_update_should_succeed=False,  # This will cause update to fail
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature\n\nThis adds a new feature.",
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["push"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed" in result.output or "failed" in result.output


def test_pr_push_success_with_existing_pr() -> None:
    """Test successful PR push with existing PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            trunk_branches={env.cwd: "main"},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},  # Clean working tree
            commit_messages_since={(env.cwd, "main"): ["Initial commit"]},
        )

        # Configure GitHub with existing PR
        pr_info = PullRequestInfoBuilder(123, "feature").build()
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={
                123: PRDetails(
                    number=123,
                    title="Feature",
                    url="https://github.com/org/repo/pull/123",
                    state="OPEN",
                    body="",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="org",
                    repo="repo",
                )
            },
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new line"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add awesome feature\n\nThis PR adds an awesome new feature.",
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["push"], obj=ctx)

        assert result.exit_code == 0
        # Verify output contains PR URL
        assert "github.com/org/repo/pull/123" in result.output

        # Verify commit message was generated
        assert len(claude_executor.prompt_calls) == 1
        prompt = claude_executor.prompt_calls[0]
        assert "feature" in prompt  # Branch name in context
        assert "main" in prompt  # Parent branch in context

        # Verify PR metadata was updated
        assert len(github.updated_pr_titles) == 1
        assert github.updated_pr_titles[0][0] == 123
        assert "awesome feature" in github.updated_pr_titles[0][1].lower()


def test_pr_push_creates_new_pr_when_none_exists() -> None:
    """Test that push creates a new PR when none exists for the branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
            trunk_branches={env.cwd: "main"},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},  # Clean working tree
            commit_messages_since={(env.cwd, "main"): ["Add new feature"]},
        )

        # Configure GitHub with no existing PR initially
        # After PR creation, we need to have it available for lookup
        github = FakeGitHub(
            authenticated=True,
            prs={},  # No PRs initially
            pr_details={
                # PR 999 is returned by create_pr() in FakeGitHub
                999: PRDetails(
                    number=999,
                    title="Add new feature",
                    url="https://github.com/org/repo/pull/999",
                    state="OPEN",
                    body="",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="org",
                    repo="repo",
                )
            },
            pr_diffs={999: "diff --git a/file.py b/file.py\n+new line"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add new feature\n\nThis adds a new feature.",
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, claude_executor=claude_executor
        )

        runner.invoke(pr_group, ["push"], obj=ctx)

        # The command should have attempted to create a PR
        assert len(github.created_prs) == 1
        created = github.created_prs[0]
        assert created[0] == "feature"  # branch
        assert created[3] == "main"  # base branch

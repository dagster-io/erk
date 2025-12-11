"""Tests for erk pr submit command.

These tests verify the CLI layer behavior of the submit command.
The command now uses Python orchestration (preflight -> generate -> finalize)
rather than delegating to a Claude slash command.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
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


def test_pr_submit_fails_when_graphite_not_authenticated() -> None:
    """Test that Graphite auth failure produces a warning (not a fatal error).

    Graphite authentication is checked in the optional 'Graphite enhancement' phase.
    The core submission (git push + gh pr create) completes successfully without Graphite.
    When Graphite enhancement fails, it's reported as a warning, not a fatal error.

    Note: This test verifies that the command handles unauthenticated Graphite gracefully
    by skipping Graphite enhancement rather than failing entirely.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure a complete PR submission scenario
        pr_info = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Feature PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Feature PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=(),
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},  # Has commits to submit
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
        )

        # Graphite not authenticated - but core submit will still work
        graphite = FakeGraphite(authenticated=False)
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new content"},
        )
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature\n\nThis adds a new feature.",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        # Command succeeds because Graphite is optional enhancement
        assert result.exit_code == 0
        # PR URL should be in output
        assert "github.com/owner/repo/pull/123" in result.output


def test_pr_submit_fails_when_github_not_authenticated() -> None:
    """Test that command fails when GitHub is not authenticated."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        # Graphite authenticated, GitHub not authenticated
        graphite = FakeGraphite(authenticated=True)
        github = FakeGitHub(authenticated=False)
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "not authenticated" in result.output


def test_pr_submit_fails_when_no_commits_ahead() -> None:
    """Test that command fails when branch has no commits ahead of parent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Configure branch with parent relationship but 0 commits ahead
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 0},  # No commits ahead
        )

        # Configure branch metadata for parent lookup
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
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "No commits ahead" in result.output


def test_pr_submit_fails_when_commit_message_generation_fails() -> None:
    """Test that command fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create PR info for the branch (so preflight can retrieve it after submit)
        pr_info = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Feature PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Feature PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=(),
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},  # Single commit - no squash needed
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
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
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new content"},
        )

        # Configure executor to fail on prompt
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="Claude CLI execution failed",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output


def test_pr_submit_fails_when_pr_update_fails() -> None:
    """Test that command fails when finalize cannot update PR metadata."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        pr_info = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Feature PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Feature PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=(),
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
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

        # Configure GitHub to fail on PR updates
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new content"},
            pr_update_should_succeed=False,
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature\n\nThis adds a new feature.",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        # The RuntimeError from FakeGitHub propagates up - command fails
        assert result.exit_code != 0
        # The exception message should be captured in the output or exception
        assert result.exception is not None or "PR update failed" in result.output


def test_pr_submit_success(tmp_path: Path) -> None:
    """Test successful PR submission with all phases completing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        pr_info = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Feature PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Feature PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=(),
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+new content"},
        )

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
        # Verify output contains PR URL
        assert "github.com/owner/repo/pull/123" in result.output

        # Verify commit message was generated
        assert len(claude_executor.prompt_calls) == 1
        prompt = claude_executor.prompt_calls[0]
        assert "feature" in prompt  # Branch name in context
        assert "main" in prompt  # Parent branch in context

        # Verify PR metadata was updated
        assert len(github.updated_pr_titles) == 1
        assert github.updated_pr_titles[0] == (123, "Add awesome feature")


def test_pr_submit_shows_graphite_url() -> None:
    """Test that Graphite URL is displayed on success."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        pr_info = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Feature PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Feature PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=(),
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+content"},
        )

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

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        # Both URLs should be in output
        assert "github.com/owner/repo/pull/123" in result.output
        assert "app.graphite" in result.output

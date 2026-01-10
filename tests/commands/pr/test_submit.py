"""Tests for erk pr submit command.

These tests verify the CLI layer behavior of the submit command.
The command now uses Python orchestration (preflight -> generate -> finalize)
rather than delegating to a Claude slash command.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
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
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+new content"},
        )

        # Graphite not authenticated - but core submit will still work
        graphite = FakeGraphite(authenticated=False)
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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

        # Configure GitHub to fail on PR updates
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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
        prompt, system_prompt = claude_executor.prompt_calls[0]
        assert "feature" in prompt  # Branch name in context
        assert "main" in prompt  # Parent branch in context

        # Verify PR metadata was updated
        assert len(github.updated_pr_titles) == 1
        assert github.updated_pr_titles[0] == (123, "Add awesome feature")


def test_pr_submit_uses_graphite_parent_for_commit_messages() -> None:
    """Test that commit messages are gathered from parent branch, not trunk.

    Regression test for issue #3197: When submitting a PR from a stacked branch,
    the commit message generator should receive only commits since the Graphite
    parent branch, not commits from the entire stack since trunk.

    Stack: main (trunk) → branch-1 → branch-2 (current)
    Expected: Only commits from branch-2 (since branch-1)
    Bug: All commits from branch-1 AND branch-2 (since main)
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        pr_info = PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/owner/repo/pull/456",
            is_draft=False,
            title="Branch 2 PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=456,
            url="https://github.com/owner/repo/pull/456",
            title="Branch 2 PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="branch-1",
            head_ref_name="branch-2",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
            labels=(),
        )

        # Configure commit messages for different base branches
        # This is the key test setup:
        # - From trunk (main): Would include ALL stack commits
        # - From parent (branch-1): Only includes this branch's commits
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "branch-1", "branch-2"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "branch-2"},
            commits_ahead={(env.cwd, "branch-1"): 1},
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
            # CRITICAL: Different commit messages depending on base branch
            commit_messages_since={
                # If incorrectly using trunk, would get all stack commits
                (env.cwd, "main"): [
                    "feat: add feature 1 (from branch-1)",
                    "feat: add feature 2 (from branch-2)",
                ],
                # If correctly using parent, gets only this branch's commits
                (env.cwd, "branch-1"): [
                    "feat: add feature 2 (from branch-2)",
                ],
            },
            diff_to_branch={(env.cwd, "branch-1"): "diff --git a/file2.py b/file2.py\n+feature 2"},
        )

        # Configure Graphite stack: main → branch-1 → branch-2
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "branch-2": BranchMetadata(
                    name="branch-2",
                    parent="branch-1",  # Parent is branch-1, NOT main
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

        github = FakeGitHub(
            authenticated=True,
            prs={"branch-2": pr_info},
            pr_details={456: pr_details},
            pr_bases={456: "branch-1"},
        )

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

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0

        # Verify the commit messages passed to Claude only include branch-2's commits
        # NOT the entire stack's commits
        assert len(claude_executor.prompt_calls) == 1
        prompt, system_prompt = claude_executor.prompt_calls[0]

        # Should contain branch-2's commit message
        assert "feat: add feature 2 (from branch-2)" in prompt

        # Should NOT contain branch-1's commit message (that would be a bug)
        assert "feat: add feature 1 (from branch-1)" not in prompt


def test_pr_submit_force_flag_bypasses_divergence_error() -> None:
    """Test that -f/--force flag allows force push when branch has diverged."""
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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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

        # Run with --force flag
        result = runner.invoke(pr_group, ["submit", "--force"], obj=ctx)

        assert result.exit_code == 0
        # Verify force was passed to push_to_remote
        assert len(git.pushed_branches) == 1
        remote, branch, set_upstream, force = git.pushed_branches[0]
        assert remote == "origin"
        assert branch == "feature"
        assert set_upstream is True
        assert force is True


def test_pr_submit_short_force_flag() -> None:
    """Test that -f short flag works the same as --force."""
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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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

        # Run with -f short flag
        result = runner.invoke(pr_group, ["submit", "-f"], obj=ctx)

        assert result.exit_code == 0
        # Verify force was passed to push_to_remote
        assert len(git.pushed_branches) == 1
        remote, branch, set_upstream, force = git.pushed_branches[0]
        assert force is True


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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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


def test_pr_submit_shows_created_message_for_new_pr() -> None:
    """Test that output shows 'created' when PR is newly created."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # No existing PR - FakeGitHub.create_pr will be called
        # and return PR #999

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
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

        # No prs configured - PR will be created new
        # pr_details must have entry for 999 (the fake PR number returned by create_pr)
        pr_details_999 = PRDetails(
            number=999,
            url="https://github.com/owner/repo/pull/999",
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

        github = FakeGitHub(
            authenticated=True,
            prs={},  # No existing PR
            pr_details={999: pr_details_999},  # Details for newly created PR
            pr_bases={999: "main"},
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
        # Should show "created" message for new PR
        assert "PR #999 created" in result.output
        # Should NOT show "found" message
        assert "found (already exists)" not in result.output


def test_pr_submit_fails_when_parent_branch_has_no_pr() -> None:
    """Test that submit fails with helpful message when parent branch has no PR.

    When submitting a branch that's part of a Graphite stack, if the parent
    branch doesn't have a PR on GitHub yet, the command should fail with
    a helpful message directing users to use 'gt submit' instead.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Current branch: feature (no existing PR)
        # Graphite parent: parent-branch (also no PR)
        # Should fail because parent needs PR first

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "parent-branch", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "parent-branch"): 1},  # Has commits to submit
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
            diff_to_branch={
                (env.cwd, "parent-branch"): "diff --git a/file.py b/file.py\n+new content"
            },
        )

        # Configure Graphite stack: main → parent-branch → feature
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="parent-branch",  # Parent is parent-branch, NOT main
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "parent-branch": BranchMetadata(
                    name="parent-branch",
                    parent="main",
                    children=["feature"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["parent-branch"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        # Neither feature nor parent-branch has a PR
        github = FakeGitHub(
            authenticated=True,
            prs={},  # No PRs exist
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

        # Should fail with helpful error message
        assert result.exit_code != 0
        assert "parent branch 'parent-branch' does not have a PR yet" in result.output
        assert "gt submit" in result.output


def test_pr_submit_shows_found_message_for_existing_pr() -> None:
    """Test that output shows 'found (already exists)' when PR already exists."""
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

        # Existing PR configured
        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},  # Existing PR
            pr_details={123: pr_details},
            pr_bases={123: "main"},
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
        # Should show "found" message for existing PR
        assert "PR #123 found (already exists)" in result.output
        # Should NOT show "created" without qualifier
        # (check it's not "PR #123 created" which would indicate the bug)
        assert "PR #123 created" not in result.output

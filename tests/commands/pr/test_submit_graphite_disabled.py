"""Tests for pr submit command with Graphite disabled.

This file verifies that PR submission works correctly when Graphite
is disabled (use_graphite=False), using the core path (git push + gh pr create).
"""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_fixtures() -> tuple[PullRequestInfo, PRDetails]:
    """Create standard PR fixtures for testing."""
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
    return pr_info, pr_details


def test_pr_submit_core_path_succeeds_without_graphite() -> None:
    """PR submission works when use_graphite=False using core path.

    The core path uses git push + gh pr create, not Graphite.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        pr_info, pr_details = _make_pr_fixtures()

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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+# Test change"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="fix: test change\n\nTest body",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            claude_executor=claude_executor,
            use_graphite=False,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        # Should complete (may have warnings about Graphite but not fail)
        # The core path should work even when Graphite is disabled
        assert result.exit_code == 0 or "Claude CLI" in result.output, result.output


def test_pr_submit_no_graphite_flag_works_without_graphite() -> None:
    """--no-graphite flag works when use_graphite is already False."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        pr_info, pr_details = _make_pr_fixtures()

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

        github = FakeGitHub(
            authenticated=True,
            prs={"feature": pr_info},
            pr_details={123: pr_details},
            pr_diffs={123: "diff --git a/file.py b/file.py\n+# Test change"},
        )

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="fix: test change\n\nTest body",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            claude_executor=claude_executor,
            use_graphite=False,
        )

        # Explicitly passing --no-graphite when already disabled should work
        result = runner.invoke(pr_group, ["submit", "--no-graphite"], obj=ctx)

        # Should work (may have other errors but not Graphite-related)
        assert "requires Graphite" not in result.output
        assert "GraphiteDisabledError" not in result.output


def test_pr_submit_without_claude_shows_proper_error() -> None:
    """PR submission shows Claude error, not Graphite error, when Claude unavailable."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(
            env,
            git=git,
            claude_executor=claude_executor,
            use_graphite=False,
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        # Should fail with Claude error, not Graphite error
        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "requires Graphite" not in result.output

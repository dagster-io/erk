"""Tests for GraphiteSubmitStrategy integration with erk pr submit command.

These tests verify that the submit command correctly uses the strategy pattern
for Graphite-first flow.
"""

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


def test_graphite_first_flow_uses_strategy() -> None:
    """Test that Graphite-first flow uses GraphiteSubmitStrategy.

    When Graphite is authenticated AND the branch is tracked, the command
    should use the strategy pattern for PR submission.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create PR info for the branch
        pr_info = PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/owner/repo/pull/456",
            is_draft=False,
            title="Feature PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        pr_details = PRDetails(
            number=456,
            url="https://github.com/owner/repo/pull/456",
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

        # Graphite authenticated AND branch tracked -> uses Graphite-first flow
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
            prs_by_branch={"feature": pr_details},
            pr_details={456: pr_details},
            pr_bases={456: "main"},
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

        # Should succeed
        assert result.exit_code == 0, f"Unexpected exit code: {result.output}"
        # Should show "Graphite Submit" phase (strategy pattern output)
        assert "Graphite Submit" in result.output
        # PR URL should be in output
        assert "github.com/owner/repo/pull/456" in result.output


def test_strategy_error_becomes_click_exception() -> None:
    """Test that strategy error is converted to ClickException with message.

    When the GraphiteSubmitStrategy returns a SubmitStrategyError,
    the submit command should convert it to a ClickException.
    """
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
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
        )

        # Graphite authenticated AND branch tracked -> uses Graphite-first flow
        # But gt submit will fail
        graphite = FakeGraphite(
            authenticated=True,
            submit_stack_raises=RuntimeError("Graphite server unavailable"),
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
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

        # Should fail with error message from strategy
        assert result.exit_code != 0
        assert "Graphite submit failed" in result.output


def test_detached_head_error_from_strategy() -> None:
    """Test that detached HEAD error from strategy is properly displayed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: None},  # Detached HEAD
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={},
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

        # This would use standard flow (no tracked branch), but detached HEAD
        # is detected early in both flows
        result = runner.invoke(pr_group, ["submit", "--no-graphite"], obj=ctx)

        # Should fail with detached HEAD error
        assert result.exit_code != 0
        # The error happens before strategy (in core submit), but message should appear
        assert "not on a branch" in result.output.lower() or "detached" in result.output.lower()

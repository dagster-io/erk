"""Tests for PR info display in wt list command.

The new fast local-only list command shows PR info from Graphite cache only.
It displays: emoji + #number (no title, no plan summary).
"""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PullRequestInfo
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_inmem_env

# ===========================
# Config Handling Tests
# ===========================


@pytest.mark.parametrize(
    ("show_pr_info", "expected_visible"),
    [
        (True, True),
        (False, False),
    ],
    ids=["visible", "hidden"],
)
def test_list_pr_visibility(show_pr_info: bool, expected_visible: bool) -> None:
    """PR info visibility follows the show_pr_info configuration flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"
        pr = PullRequestInfo(
            number=42,
            state="OPEN",
            url="https://github.com/owner/repo/pull/42",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        # PR data comes from Graphite cache
        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={branch_name: pr}),
            use_graphite=True,
            show_pr_info=show_pr_info,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        assert ("#42" in result.output) is expected_visible


# ===========================
# Emoji Rendering Tests
# ===========================


@pytest.mark.parametrize(
    "state,is_draft,checks,expected_emoji",
    [
        ("OPEN", False, True, "✅"),  # Open PR with passing checks
        ("OPEN", False, False, "❌"),  # Open PR with failing checks
        ("OPEN", False, None, "👀"),  # Open PR with no checks
        ("OPEN", True, None, "🚧"),  # Draft PR
        ("MERGED", False, True, "🎉"),  # Merged PR
        ("CLOSED", False, None, "⛔"),  # Closed (not merged) PR
    ],
)
def test_list_pr_emoji_mapping(
    state: str, is_draft: bool, checks: bool | None, expected_emoji: str
) -> None:
    """Verify PR state → emoji mapping for all cases."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "test-branch"

        # Use builder pattern for PR creation
        builder = PullRequestInfoBuilder(number=100, branch=branch_name)
        builder.state = state
        builder.is_draft = is_draft
        builder.checks_passing = checks
        pr = builder.build()

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify emoji appears in output
        assert expected_emoji in result.output
        assert "#100" in result.output


# ===========================
# Merge Conflict Tests
# ===========================


def test_list_pr_with_merge_conflicts() -> None:
    """Test that PRs with merge conflicts show the conflict emoji 💥."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "conflict-branch"

        # Create PR with conflicts
        pr = PullRequestInfo(
            number=200,
            state="OPEN",
            url="https://github.com/testowner/testrepo/pull/200",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
            has_conflicts=True,  # This PR has merge conflicts
        )

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify both the base emoji and conflict emoji appear
        assert "✅💥" in result.output  # PR with passing checks and conflicts
        assert "#200" in result.output


# ===========================
# Graceful Degradation Tests
# ===========================


def test_list_graceful_degradation_no_graphite_cache() -> None:
    """Test that list works gracefully when Graphite cache is not available."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        # Empty Graphite - simulates no cache
        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={}),  # No PR info available
            use_graphite=True,
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        # Should succeed even without PR info
        assert result.exit_code == 0, result.output

        # Should still show worktree info
        assert "root" in result.output
        assert branch_name in result.output

        # PR column should show "-" for no PR info
        assert "-" in result.output


def test_list_github_api_fallback_when_graphite_empty() -> None:
    """Test that PR info falls back to GitHub API when Graphite cache is empty."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"
        pr = PullRequestInfo(
            number=999,
            state="OPEN",
            url="https://github.com/owner/repo/pull/999",
            is_draft=False,
            title="Test PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        # Empty Graphite cache (simulates Graphite disabled or no cache)
        # but GitHub has the PR data
        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(pr_info={}),  # Empty - no Graphite cache
            github=FakeGitHub(prs={branch_name: pr}),  # GitHub has the PR
            use_graphite=False,  # Graphite disabled
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # PR info should come from GitHub API fallback
        assert "#999" in result.output

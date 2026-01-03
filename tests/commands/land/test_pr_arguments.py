"""Tests for erk land command with PR arguments.

The land command can accept:
- PR number (e.g., erk land 123)
- PR URL (e.g., erk land https://github.com/owner/repo/pull/123)
- Branch name (e.g., erk land feature-1)
"""

from dataclasses import replace

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_by_number() -> None:
    """Test erk land 123 lands the specified PR by number."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},  # Running from main, not feature-1
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={123: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        # Pass "123" as the PR number argument with --force to skip confirmation
        result = runner.invoke(
            cli, ["land", "123", "--script", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch was deleted
        assert "feature-1" in git_ops.deleted_branches


def test_land_by_url() -> None:
    """Test erk land <url> lands the specified PR by URL."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=456,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/456",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                456: PRDetails(
                    number=456,
                    url="https://github.com/owner/repo/pull/456",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={456: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        # Pass URL as the argument
        result = runner.invoke(
            cli,
            ["land", "https://github.com/owner/repo/pull/456", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 456 in github_ops.merged_prs

        # Verify worktree was removed
        assert feature_1_path in git_ops.removed_worktrees


def test_land_by_branch_name() -> None:
    """Test erk land <branch> lands the branch's PR."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},  # Running from main
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={123: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            cli,
            ["land", "feature-1", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch was deleted
        assert "feature-1" in git_ops.deleted_branches


def test_land_fork_pr() -> None:
    """Test landing a fork PR uses pr/{number} branch naming."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            }
        )

        # Fork PR - is_cross_repository=True
        github_ops = FakeGitHub(
            pr_details={
                789: PRDetails(
                    number=789,
                    url="https://github.com/owner/repo/pull/789",
                    title="Fork PR",
                    body="PR from fork",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="contributor-feature",  # Fork branch name
                    is_cross_repository=True,  # Fork PR
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={789: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            cli, ["land", "789", "--script", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 789 in github_ops.merged_prs

        # For fork PRs, we expect "pr/789" branch naming convention
        assert "Merged PR #789 [pr/789]" in result.output

        # The fork PR's branch doesn't exist locally (never checked out),
        # so we skip deletion silently (no confusing message)
        assert "Branch 'pr/789' not found locally" not in result.output
        assert "pr/789" not in git_ops.deleted_branches

"""Tests for erk br land command."""

from dataclasses import replace
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.branch import branch_group
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.env_helpers import erk_inmem_env


def test_br_land_by_branch_name() -> None:
    """Test erk br land <branch> lands the branch's PR."""
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
            branch_group,
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


def test_br_land_no_pr_for_branch() -> None:
    """Test error when branch has no associated PR."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

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

        # No PRs configured
        github_ops = FakeGitHub()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            branch_group,
            ["land", "feature-1", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "No pull request found for branch 'feature-1'" in result.output


def test_br_land_from_target_branch() -> None:
    """Test landing from the target branch's worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        # We're on feature-1, landing feature-1's PR
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # On the target branch
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
            branch_group,
            ["land", "feature-1", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Since we were in the deleted worktree, we should navigate to root
        # Verify activation script was generated
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_br_land_force_skips_confirmation() -> None:
    """Test that --force skips cleanup confirmation."""
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

        # Use --force to skip confirmation (no input needed)
        result = runner.invoke(
            branch_group,
            ["land", "feature-1", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify worktree was removed (--force skipped confirmation)
        assert feature_1_path in git_ops.removed_worktrees


def test_br_land_pr_not_open() -> None:
    """Test error when PR is not open."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

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

        # PR is already merged
        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="MERGED",  # Not open
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
                    state="MERGED",  # Not open
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
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            branch_group,
            ["land", "feature-1", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "is not open" in result.output


def test_br_land_pr_base_not_trunk() -> None:
    """Test error when PR base branch is not trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # PR targets feature-1, not main
        github_ops = FakeGitHub(
            prs={
                "feature-2": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 2",
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
                    title="Feature 2",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="feature-1",  # Not trunk
                    head_ref_name="feature-2",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            branch_group,
            ["land", "feature-2", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "targets 'feature-1' but should target 'main'" in result.output

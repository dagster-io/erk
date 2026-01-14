"""Tests for erk land command --up flag behavior.

The --up flag navigates to the child branch after landing.
"""

from pathlib import Path

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


def test_land_with_up_navigates_to_child_branch() -> None:
    """Test --up navigates to child branch after landing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        feature_2_path = repo_dir / "worktrees" / "feature-2"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        # feature-1 is parent of feature-2 (feature-1 has one child)
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
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
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
        )

        result = runner.invoke(
            cli, ["land", "--script", "--up", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree of feature-1 was NOT removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees

        # Verify branch feature-1 was deleted (via Graphite gateway since use_graphite=True)
        assert any(branch == "feature-1" for _path, branch in graphite_ops.delete_branch_calls)

        # Verify activation script points to feature-2 worktree (the child)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_2_path) in script_content


def test_land_with_up_no_children_fails_before_merge() -> None:
    """Test --up fails BEFORE merge when no children exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        # feature-1 has NO children
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
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["land", "--script", "--up", "--force"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail with exit code 1
        assert result.exit_code == 1

        # Should show error about no children
        assert "Cannot use --up" in result.output
        assert "has no children" in result.output
        assert "Use 'erk land' without --up" in result.output

        # CRITICAL: PR should NOT have been merged (fail-fast)
        assert len(github_ops.merged_prs) == 0


def test_land_with_up_multiple_children_fails_before_merge() -> None:
    """Test --up fails BEFORE merge when multiple children exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees(
                "main", ["feature-1", "feature-2a", "feature-2b"], repo_dir=repo_dir
            ),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        # feature-1 has MULTIPLE children
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2a", "feature-2b"], commit_sha="def456"
                ),
                "feature-2a": BranchMetadata.branch("feature-2a", "feature-1", commit_sha="ghi789"),
                "feature-2b": BranchMetadata.branch("feature-2b", "feature-1", commit_sha="jkl012"),
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
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["land", "--script", "--up", "--force"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail with exit code 1
        assert result.exit_code == 1

        # Should show error about multiple children
        assert "Cannot use --up" in result.output
        assert "has multiple children" in result.output
        assert "'feature-2a'" in result.output
        assert "'feature-2b'" in result.output
        assert "erk co <branch>" in result.output

        # CRITICAL: PR should NOT have been merged (fail-fast)
        assert len(github_ops.merged_prs) == 0


def test_land_with_up_uses_main_repo_root_after_worktree_deletion() -> None:
    """Test --up uses main_repo_root (not deleted worktree path) for navigation.

    This regression test verifies fix for issue where repo.root pointed to the
    deleted worktree directory. After deletion, find_worktree_for_branch() was
    called with the stale repo.root path, causing worktree lookup to fail.

    The fix creates post_deletion_repo with root=main_repo_root before navigation.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        feature_2_path = repo_dir / "worktrees" / "feature-2"

        # Key setup: worktrees are keyed by env.cwd (main repo root)
        # This simulates running from inside a linked worktree
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            # Current branch is feature-1, being run from feature-1 worktree
            current_branches={feature_1_path: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={feature_1_path: env.git_dir, env.cwd: env.git_dir},
            # CRITICAL: repository_root for feature_1_path must return feature_1_path
            # (the worktree path itself), not the main repo root. This simulates
            # how git --show-toplevel returns the worktree path when inside a worktree.
            repository_roots={feature_1_path: feature_1_path, env.cwd: env.cwd},
            file_statuses={feature_1_path: ([], [], [])},
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

        # CRITICAL: repo.root is the worktree path (that will be deleted)
        # repo.main_repo_root is the main repo root (env.cwd)
        # After worktree deletion, only main_repo_root is valid for worktree lookups
        repo = RepoContext(
            root=feature_1_path,  # Worktree path being deleted!
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
            main_repo_root=env.cwd,  # Main repo root (stays valid)
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            cwd=feature_1_path,  # Running from worktree
            issues=issues_ops,
        )

        # Without the fix: find_worktree_for_branch(feature_1_path, "feature-2")
        # would fail because feature_1_path is no longer in any worktree list
        # after deletion.
        #
        # With the fix: find_worktree_for_branch(main_repo_root, "feature-2")
        # succeeds because main_repo_root is the dict key for worktrees.
        result = runner.invoke(
            cli, ["land", "--script", "--up", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree of feature-1 was NOT removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees

        # Verify branch feature-1 was deleted (via Graphite gateway since use_graphite=True)
        assert any(branch == "feature-1" for _path, branch in graphite_ops.delete_branch_calls)

        # Verify activation script points to feature-2 worktree (the child)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_2_path) in script_content

        # CRITICAL: Verify no new worktree was created for feature-2
        # The bug was that find_worktree_for_branch couldn't find the existing
        # worktree, causing it to unnecessarily create a new one.
        # With the fix, the existing worktree should be found directly.
        assert len(git_ops.added_worktrees) == 0, (
            "Should find existing worktree, not create a new one. "
            f"Added worktrees: {git_ops.added_worktrees}"
        )

"""Tests for erk land command confirmation prompts and context validation.

Tests for:
- Cleanup confirmation (delete worktree/branch)
- --force flag to skip confirmations
- --up rejection with PR argument
- Landing from different worktree
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_execute_always_deletes_branch() -> None:
    """Test that execute mode always deletes branch (no confirmations).

    With deferred execution, the execute phase uses force=True internally
    because all user confirmations happen during the validation phase.
    The activation script is only generated if the user approved all prompts
    during validation.

    This test verifies execute mode behavior: branch is always deleted
    without prompting, since confirmation happened during validation.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",
                feature_1_path: "feature-1",  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_1_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_1_path: env.cwd},
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

        # Execute mode: branch is always deleted (no confirmation in execute phase)
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                "--branch=feature-1",
                f"--worktree-path={feature_1_path}",
                "--is-current-branch",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree was NOT removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees

        # Verify branch was deleted (execute mode uses force=True, no confirmation)
        assert any(branch == "feature-1" for _path, branch in graphite_ops.delete_branch_calls)

        # Verify the "Deleted branch" message
        assert "Deleted branch (worktree 'feature-1' detached at 'main')" in result.output


def test_land_force_skips_cleanup_confirmation() -> None:
    """Test that execute mode always runs cleanup (no confirmations needed).

    With deferred execution, the execute phase uses force=True internally
    because all user confirmations happen during the validation phase.
    This test verifies that execute phase runs cleanup without prompting.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",
                feature_1_path: "feature-1",  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_1_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_1_path: env.cwd},
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

        # Execute mode: no --force needed, execute phase always runs without prompts
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                "--branch=feature-1",
                f"--worktree-path={feature_1_path}",
                "--is-current-branch",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree was NOT removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees

        # Verify branch was deleted (via Graphite gateway since use_graphite=True)
        assert any(branch == "feature-1" for _path, branch in graphite_ops.delete_branch_calls)


def test_land_up_rejected_with_pr_argument() -> None:
    """Test that --up is rejected when a PR number is specified."""
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

        # Try to use --up with PR number
        result = runner.invoke(
            cli, ["land", "123", "--script", "--up"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail
        assert result.exit_code == 1

        # Should show error about --up not allowed with PR argument
        assert "Cannot use --up when specifying a PR" in result.output

        # PR should NOT have been merged (fail-fast)
        assert len(github_ops.merged_prs) == 0


def test_land_from_different_worktree() -> None:
    """Test landing a PR from a different worktree than the PR's branch.

    With deferred execution, this test verifies the execute phase behavior
    when landing a PR from a different worktree (--is-current-branch is NOT set).
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        # We're on main, landing feature-1's PR
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",  # On main
                feature_1_path: "feature-1",  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_1_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_1_path: env.cwd},
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

        # Execute mode without --is-current-branch (landing from different worktree)
        # No --force needed: execute phase always runs without prompts
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                "--branch=feature-1",
                f"--worktree-path={feature_1_path}",
                # Note: NOT passing --is-current-branch
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree was NOT removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees

        # Verify branch was deleted (via Graphite gateway since use_graphite=True)
        assert any(branch == "feature-1" for _path, branch in graphite_ops.delete_branch_calls)

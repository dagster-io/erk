"""Tests for erk land command unresolved review comments warnings.

Tests for behavior when PRs have unresolved review comments:
- Warning shown with prompt to continue
- --force skips the warning
- User can confirm to proceed despite warning
- Non-interactive mode fails with error when unresolved comments exist
"""

from dataclasses import replace

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import PRDetails, PRReviewThread, PullRequestInfo
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_warns_on_unresolved_comments() -> None:
    """Test land shows warning when PR has unresolved review comments."""
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
            pr_bases={123: "main"},
            merge_should_succeed=True,
            # Configure unresolved review threads
            pr_review_threads={
                123: [
                    PRReviewThread(
                        id="thread1",
                        path="src/main.py",
                        line=10,
                        is_resolved=False,
                        is_outdated=False,
                        comments=(),
                    ),
                    PRReviewThread(
                        id="thread2",
                        path="src/utils.py",
                        line=20,
                        is_resolved=False,
                        is_outdated=False,
                        comments=(),
                    ),
                ]
            },
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # User declines to continue when prompted about unresolved comments
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[False],  # Decline unresolved comments prompt
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should exit cleanly (user chose not to continue)
        assert result.exit_code == 0

        # Should show warning about unresolved comments
        assert "has 2 unresolved review comment(s)" in result.output

        # PR should NOT have been merged (user declined)
        assert len(github_ops.merged_prs) == 0


def test_land_force_skips_unresolved_comments_warning() -> None:
    """Test --force skips the unresolved comments confirmation."""
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
            # Configure unresolved review threads
            pr_review_threads={
                123: [
                    PRReviewThread(
                        id="thread1",
                        path="src/main.py",
                        line=10,
                        is_resolved=False,
                        is_outdated=False,
                        comments=(),
                    ),
                ]
            },
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
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        # Use --force to skip all confirmations
        result = runner.invoke(
            cli,
            ["land", "123", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should NOT prompt about unresolved comments when --force is used
        assert "Continue anyway?" not in result.output

        # PR should have been merged
        assert 123 in github_ops.merged_prs

        # Worktree should NOT be removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees


def test_land_proceeds_when_user_confirms_unresolved_comments() -> None:
    """Test land proceeds when user confirms despite unresolved comments."""
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
            # Configure unresolved review threads
            pr_review_threads={
                123: [
                    PRReviewThread(
                        id="thread1",
                        path="src/main.py",
                        line=10,
                        is_resolved=False,
                        is_outdated=False,
                        comments=(),
                    ),
                ]
            },
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # User confirms both prompts (unresolved comments + cleanup)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[True, True],  # Confirm unresolved comments, confirm cleanup
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show warning about unresolved comments
        assert "has 1 unresolved review comment(s)" in result.output

        # PR should have been merged (user confirmed)
        assert 123 in github_ops.merged_prs

        # Worktree should NOT be removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees


def test_land_handles_rate_limit_gracefully() -> None:
    """Test land continues with warning when GraphQL API is rate limited.

    When the GitHub GraphQL API returns a rate limit error for review threads,
    the land command should show a warning and continue instead of crashing.
    """
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
            review_threads_rate_limited=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Confirm branch deletion prompt
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[True],  # Confirm branch deletion
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show rate limit warning (not crash)
        assert "Could not check for unresolved comments (API rate limited)" in result.output

        # PR should have been merged (rate limit on review threads shouldn't block)
        assert 123 in github_ops.merged_prs

        # Worktree should NOT be removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees


def test_land_fails_non_interactive_with_unresolved_comments() -> None:
    """Test land fails in non-interactive mode when PR has unresolved comments.

    When running in a non-TTY context (e.g., from TUI or CI), land should fail
    with an error message instead of hanging waiting for user input.
    """
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
            pr_bases={123: "main"},
            merge_should_succeed=True,
            # Configure unresolved review threads
            pr_review_threads={
                123: [
                    PRReviewThread(
                        id="thread1",
                        path="src/main.py",
                        line=10,
                        is_resolved=False,
                        is_outdated=False,
                        comments=(),
                    ),
                ]
            },
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Non-interactive mode: console has no confirm_responses (would raise)
        console = FakeConsole(
            is_interactive=False,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,
        )
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            console=console,
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        # Run in non-interactive mode
        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should fail with exit code 1
        assert result.exit_code == 1

        # Should show warning about unresolved comments
        assert "has 1 unresolved review comment(s)" in result.output

        # Should show error about non-interactive mode
        assert "Cannot prompt for confirmation in non-interactive mode" in result.output
        assert "Use --force to skip this check" in result.output

        # PR should NOT have been merged
        assert len(github_ops.merged_prs) == 0

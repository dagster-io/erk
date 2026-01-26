"""Tests for erk land command unresolved review comments warnings.

Tests for behavior when PRs have unresolved review comments:
- Warning shown with prompt to continue
- Execute mode skips the warning (no prompts in execute phase)
- User can confirm to proceed despite warning
- Non-interactive mode fails with error when unresolved comments exist
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails, PRReviewThread, PullRequestInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
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
            issues=issues_ops,
        )

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
    """Test execute mode runs without unresolved comments confirmation.

    With deferred execution, the execute phase uses force=True internally
    because all user confirmations happen during the validation phase.
    This test verifies that execute phase runs without prompting.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
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
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
        )

        # Execute mode: no prompts needed, execute phase always runs without confirmations
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                "--branch=feature-1",
                f"--worktree-path={feature_1_path}",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should NOT prompt about unresolved comments in execute phase
        assert "Continue anyway?" not in result.output

        # PR should have been merged
        assert 123 in github_ops.merged_prs

        # Worktree should NOT be removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees


def test_land_proceeds_when_user_confirms_unresolved_comments() -> None:
    """Test land proceeds when user confirms despite unresolved comments.

    With deferred execution, this test verifies the execute phase behavior
    when user confirms cleanup during execution.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
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

        # User confirms cleanup prompt
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[True],  # Confirm cleanup
            issues=issues_ops,
        )

        # Execute mode: cleanup confirmation happens during execution
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                "--branch=feature-1",
                f"--worktree-path={feature_1_path}",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # PR should have been merged (user confirmed)
        assert 123 in github_ops.merged_prs

        # Worktree should NOT be removed (worktrees are always preserved)
        assert feature_1_path not in git_ops.removed_worktrees


def test_land_handles_rate_limit_gracefully() -> None:
    """Test land continues with warning when GraphQL API is rate limited.

    When the GitHub GraphQL API returns a rate limit error for review threads,
    the land command should show a warning and continue instead of crashing.

    With deferred execution, this test verifies the execute phase behavior
    when rate limit warning is shown during validation.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
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
            issues=issues_ops,
        )

        # Execute mode: PR merge happens during execution
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                "--branch=feature-1",
                f"--worktree-path={feature_1_path}",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

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
            issues=issues_ops,
        )

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

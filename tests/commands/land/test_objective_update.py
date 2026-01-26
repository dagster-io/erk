"""Tests for objective update prompt in erk land command.

Tests the behavior when landing a PR linked to an objective:
- Execute mode always runs objective update without prompting
- User confirming prompt runs Claude streaming
- Claude execution failure shows warning with retry command
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _create_plan_issue_with_objective(objective_number: int) -> IssueInfo:
    """Create a plan issue with objective_issue in plan-header metadata."""
    body = format_plan_header_body_for_test(
        created_at=datetime.now(UTC).isoformat(),
        created_by="testuser",
        objective_issue=objective_number,
    )
    return IssueInfo(
        number=42,
        title="P42: Test Plan",
        body=body,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def test_land_force_runs_objective_update_without_prompt() -> None:
    """Test that execute mode always runs objective update without prompting.

    With deferred execution, the execute phase uses force=True internally
    because all user confirmations happen during the validation phase.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"
        feature_worktree_path = repo_dir / "worktrees" / feature_branch

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
                feature_worktree_path: feature_branch,  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_worktree_path: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=[feature_branch], commit_sha="abc123"
                ),
                feature_branch: BranchMetadata.branch(feature_branch, "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                feature_branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test Feature",
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
                    title="Test Feature",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name=feature_branch,
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

        # Create plan issue #42 with objective link to #100
        plan_issue = _create_plan_issue_with_objective(objective_number=100)
        issues_ops = FakeGitHubIssues(username="testuser", issues={42: plan_issue})

        executor = FakeClaudeExecutor()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Execute mode: objective update runs automatically without prompting
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
            claude_executor=executor,
        )

        # Execute mode with objective number - no --force needed
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--objective-number=100",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show objective info and success message
        assert "Linked to Objective #100" in result.output
        assert "Starting objective update..." in result.output
        assert "Objective updated successfully" in result.output

        # Should have called claude executor with correct command
        assert len(executor.executed_commands) == 1
        cmd, path, dangerous, verbose, model = executor.executed_commands[0]
        expected = (
            "/erk:objective-update-with-landed-pr "
            "--pr 123 --objective 100 --branch P42-test-feature --auto-close"
        )
        assert cmd == expected
        assert dangerous is True


def test_land_execute_always_runs_objective_update() -> None:
    """Test that execute mode always runs objective update (no confirmation).

    With deferred execution, the execute phase uses force=True internally
    because all user confirmations happen during the validation phase.
    If an objective number is provided to execute mode, the objective
    update always runs without prompting.

    This test verifies execute mode behavior: objective update always runs
    when objective_number is provided, since confirmation would have
    happened during validation.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"
        feature_worktree_path = repo_dir / "worktrees" / feature_branch

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
                feature_worktree_path: feature_branch,  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_worktree_path: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=[feature_branch], commit_sha="abc123"
                ),
                feature_branch: BranchMetadata.branch(feature_branch, "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                feature_branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test Feature",
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
                    title="Test Feature",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name=feature_branch,
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

        plan_issue = _create_plan_issue_with_objective(objective_number=100)
        issues_ops = FakeGitHubIssues(username="testuser", issues={42: plan_issue})

        executor = FakeClaudeExecutor()

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
            claude_executor=executor,
        )

        # Execute mode with objective number - always runs update
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--objective-number=100",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Execute mode always runs objective update (no confirmation)
        assert "Objective updated successfully" in result.output

        # Should have called claude executor
        assert len(executor.executed_commands) == 1


def test_land_user_confirms_objective_update_runs_claude() -> None:
    """Test that user confirming prompt runs Claude streaming and succeeds.

    With deferred execution, this test verifies the execute phase behavior.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"
        feature_worktree_path = repo_dir / "worktrees" / feature_branch

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
                feature_worktree_path: feature_branch,  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_worktree_path: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=[feature_branch], commit_sha="abc123"
                ),
                feature_branch: BranchMetadata.branch(feature_branch, "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                feature_branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test Feature",
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
                    title="Test Feature",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name=feature_branch,
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

        plan_issue = _create_plan_issue_with_objective(objective_number=100)
        issues_ops = FakeGitHubIssues(username="testuser", issues={42: plan_issue})

        # Default executor simulates success
        executor = FakeClaudeExecutor()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # User says:
        # "y" to objective update
        # "y" to worktree cleanup
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[
                True,  # Confirm objective update
                True,  # Confirm cleanup
            ],
            issues=issues_ops,
            claude_executor=executor,
        )

        # Execute mode with objective number
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--objective-number=100",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show feedback before and after streaming
        assert "Starting objective update..." in result.output
        assert "Objective updated successfully" in result.output

        # Should have called claude executor streaming with correct command
        assert len(executor.executed_commands) == 1
        cmd, path, dangerous, verbose, model = executor.executed_commands[0]
        expected = (
            "/erk:objective-update-with-landed-pr "
            "--pr 123 --objective 100 --branch P42-test-feature --auto-close"
        )
        assert cmd == expected
        assert dangerous is True


def test_land_claude_failure_shows_retry_command() -> None:
    """Test that Claude streaming failure shows warning and manual command.

    With deferred execution, this test verifies the execute phase behavior.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"
        feature_worktree_path = repo_dir / "worktrees" / feature_branch

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
                feature_worktree_path: feature_branch,  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, feature_worktree_path: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=[feature_branch], commit_sha="abc123"
                ),
                feature_branch: BranchMetadata.branch(feature_branch, "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                feature_branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test Feature",
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
                    title="Test Feature",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name=feature_branch,
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

        plan_issue = _create_plan_issue_with_objective(objective_number=100)
        issues_ops = FakeGitHubIssues(username="testuser", issues={42: plan_issue})

        # Configure executor to simulate failure
        executor = FakeClaudeExecutor(command_should_fail=True)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # User says:
        # "y" to objective update
        # "y" to worktree cleanup
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[
                True,  # Confirm objective update
                True,  # Confirm cleanup
            ],
            issues=issues_ops,
            claude_executor=executor,
        )

        # Execute mode with objective number
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--objective-number=100",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show starting feedback and failure message with manual retry command
        assert "Starting objective update..." in result.output
        assert "failed" in result.output.lower()
        assert "/erk:objective-update-with-landed-pr" in result.output
        assert "manually" in result.output.lower()

        # Should have tried to call claude executor
        assert len(executor.executed_commands) == 1

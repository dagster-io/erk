"""Tests for objective update prompt in erk land command.

Tests the behavior when landing a PR linked to an objective:
- --force skips the prompt and prints command for later
- User declining prompt skips update and shows command
- User confirming prompt runs Claude streaming
- Claude execution failure shows warning with retry command
"""

from dataclasses import replace
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import format_plan_header_body
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.env_helpers import erk_inmem_env


def _create_plan_issue_with_objective(objective_number: int) -> IssueInfo:
    """Create a plan issue with objective_issue in plan-header metadata."""
    # Create the plan-header body with objective_issue field
    body = format_plan_header_body(
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
    """Test that --force flag runs objective update without prompting."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
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

        # With --force, objective update runs automatically
        # Decline closing plan issue (missing closing ref prompt)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[False],  # Decline closing plan issue prompt
        )
        test_ctx = replace(test_ctx, issues=issues_ops, claude_executor=executor)

        result = runner.invoke(
            cli,
            ["land", "123", "--script", "--force"],
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


def test_land_user_declines_objective_update_shows_command() -> None:
    """Test that user declining prompt skips update and shows command."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
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

        # User says "n" to close plan issue, "n" to objective update, "y" to worktree cleanup
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[
                False,
                False,
                True,
            ],  # Decline close, decline update, confirm cleanup
        )
        test_ctx = replace(test_ctx, issues=issues_ops, claude_executor=executor)

        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show skip message with command
        assert "Skipped" in result.output
        assert "/erk:objective-update-with-landed-pr" in result.output

        # Should NOT have called claude executor
        assert len(executor.executed_commands) == 0


def test_land_user_confirms_objective_update_runs_claude() -> None:
    """Test that user confirming prompt runs Claude streaming and succeeds."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
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

        # User says "n" to close plan issue, "y" to objective update, "y" to worktree cleanup
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[False, True, True],  # Decline close, confirm update, confirm cleanup
        )
        test_ctx = replace(test_ctx, issues=issues_ops, claude_executor=executor)

        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
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
    """Test that Claude streaming failure shows warning and manual command."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_branch = "P42-test-feature"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
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

        # User says "n" to close plan issue, "y" to objective update, "y" to worktree cleanup
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            confirm_responses=[False, True, True],  # Decline close, confirm update, confirm cleanup
        )
        test_ctx = replace(test_ctx, issues=issues_ops, claude_executor=executor)

        result = runner.invoke(
            cli,
            ["land", "123", "--script"],
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

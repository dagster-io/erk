"""Tests for objective auto-detection in land-execute command.

Tests that objective is automatically detected from branch name when
--objective-number is not explicitly provided.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _create_plan_issue_with_objective(
    *,
    plan_number: int,
    objective_number: int,
) -> IssueInfo:
    """Create a plan issue with objective_issue in plan-header metadata."""
    body = format_plan_header_body_for_test(
        created_at=datetime.now(UTC).isoformat(),
        created_by="testuser",
        objective_issue=objective_number,
    )
    return IssueInfo(
        number=plan_number,
        title=f"P{plan_number}: Test Plan",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{plan_number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def test_land_execute_auto_detects_objective_from_branch() -> None:
    """Test that objective is auto-detected when --objective-number is not provided.

    When landing a branch named P42-feature (linked to plan issue #42),
    and plan issue #42 has objective_id=100, the objective update should
    be triggered with objective #100 even without --objective-number flag.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        # Branch name P42-... indicates link to plan issue #42
        feature_branch = "P42-test-feature"
        feature_worktree_path = repo_dir / "worktrees" / feature_branch

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
                feature_worktree_path: feature_branch,
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
        plan_issue = _create_plan_issue_with_objective(
            plan_number=42,
            objective_number=100,
        )
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

        # Execute WITHOUT --objective-number flag - should auto-detect from branch
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--use-graphite",
                "--script",
                # NOTE: --objective-number is NOT provided
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show objective info - this proves auto-detection worked
        assert "Linked to Objective #100" in result.output
        assert "Starting objective update..." in result.output
        assert "Objective updated successfully" in result.output

        # Verify Claude executor was called with correct objective number
        assert len(executor.executed_commands) == 1
        cmd, _path, dangerous, _verbose, _model = executor.executed_commands[0]
        # The command should include objective 100 (auto-detected from plan issue #42)
        assert "--objective 100" in cmd
        assert "--pr 123" in cmd
        assert "--branch P42-test-feature" in cmd
        assert dangerous is True


def test_land_execute_explicit_objective_takes_precedence() -> None:
    """Test that explicit --objective-number takes precedence over auto-detection.

    Even when the branch is linked to a plan with an objective, if the user
    explicitly provides --objective-number, that value should be used.
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
                feature_worktree_path: feature_branch,
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

        # Plan issue #42 has objective_id=100
        plan_issue = _create_plan_issue_with_objective(
            plan_number=42,
            objective_number=100,
        )
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

        # Execute WITH explicit --objective-number=200 (different from plan's 100)
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--objective-number=200",  # Explicitly provided, different from plan
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should use the explicit objective number 200, not the auto-detected 100
        assert "Linked to Objective #200" in result.output

        # Verify Claude executor was called with explicit objective number
        assert len(executor.executed_commands) == 1
        cmd, _path, _dangerous, _verbose, _model = executor.executed_commands[0]
        assert "--objective 200" in cmd  # Uses explicit value, not 100


def test_land_execute_no_objective_when_plan_has_no_objective() -> None:
    """Test that no objective update is triggered when plan has no objective_id.

    When the plan issue has no objective_id in its metadata, the objective
    update should not be triggered.
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
                feature_worktree_path: feature_branch,
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

        # Plan issue #42 WITHOUT objective_id
        body = format_plan_header_body_for_test(
            created_at=datetime.now(UTC).isoformat(),
            created_by="testuser",
            # No objective_issue parameter - defaults to None
        )
        plan_issue = IssueInfo(
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

        # Execute without --objective-number - plan has no objective_id
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should NOT show objective info - no objective detected
        assert "Linked to Objective" not in result.output

        # Claude executor should NOT have been called
        assert len(executor.executed_commands) == 0


def test_land_execute_no_objective_when_branch_not_linked_to_plan() -> None:
    """Test that no objective update is triggered for non-plan branches.

    When the branch name doesn't have a P<number>- prefix, no objective
    detection should occur.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        # Branch WITHOUT P<number>- prefix
        feature_branch = "regular-feature"
        feature_worktree_path = repo_dir / "worktrees" / feature_branch

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [feature_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: "main",
                feature_worktree_path: feature_branch,
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

        issues_ops = FakeGitHubIssues(username="testuser")

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

        # Execute without --objective-number - branch not linked to plan
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should NOT show objective info
        assert "Linked to Objective" not in result.output

        # Claude executor should NOT have been called
        assert len(executor.executed_commands) == 0

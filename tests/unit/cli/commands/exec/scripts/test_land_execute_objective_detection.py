"""Tests for objective update behavior in land-execute.

After migrating objective update into land-execute, --objective-number triggers
the objective update inline (after successful merge). Without the flag, no
auto-detection occurs and no Claude calls are made.
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
from tests.fakes.prompt_executor import FakePromptExecutor
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


def test_land_execute_no_objective_auto_detection() -> None:
    """Test that objective is NOT auto-detected from branch name.

    land-execute no longer performs auto-detection. Even when the branch
    is linked to a plan with an objective, no Claude calls should occur.
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

        plan_issue = _create_plan_issue_with_objective(
            plan_number=42,
            objective_number=100,
        )
        issues_ops = FakeGitHubIssues(username="testuser", issues={42: plan_issue})

        executor = FakePromptExecutor()

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
            prompt_executor=executor,
        )

        # Execute WITHOUT --objective-number flag
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

        # Should NOT show objective info - no auto-detection
        assert "Linked to Objective" not in result.output

        # Claude executor should NOT have been called
        assert len(executor.executed_commands) == 0


def test_land_execute_with_objective_triggers_update() -> None:
    """Test that --objective-number triggers objective update after merge.

    When --objective-number is passed, land-execute calls the objective
    update helper after successfully merging the PR.
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

        plan_issue = _create_plan_issue_with_objective(
            plan_number=42,
            objective_number=100,
        )
        issues_ops = FakeGitHubIssues(username="testuser", issues={42: plan_issue})

        executor = FakePromptExecutor()

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
            prompt_executor=executor,
        )

        # Execute WITH --objective-number=200 (should trigger update)
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=123",
                f"--branch={feature_branch}",
                f"--worktree-path={feature_worktree_path}",
                "--objective-number=200",
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show objective info
        assert "Linked to Objective #200" in result.output

        # Claude executor should have been called for objective update
        assert len(executor.executed_commands) == 1
        cmd = executor.executed_commands[0][0]
        assert "/erk:objective-update-with-landed-pr" in cmd
        assert "--objective 200" in cmd
        assert "--pr 123" in cmd
        assert f"--branch {feature_branch}" in cmd

"""Tests for skipping learn prompt on remote PRs.

When landing a PR via `erk land <url>` or `erk land <number>` for a branch
that has NO local worktree, the learn status check should be skipped because
there are no local Claude sessions to learn from.

Regression test for issue #4871.
"""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.graphite import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_skips_learn_prompt_for_remote_pr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that learn prompt is skipped when landing a PR with no local worktree.

    When running `erk land <url>` for a remote PR (no local worktree), the learn
    status check should not run because there are no local Claude sessions to
    learn from.

    This is a regression test for issue #4871 where `erk land <remote-url>` was
    incorrectly prompting "Warning: Plan #X has not been learned from."

    With deferred execution, this test verifies the execute phase behavior.
    """
    from tests.fakes.gateway.console import FakeConsole

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Branch name follows plan pattern (starts with issue number)
        plan_branch = "4867-fix-something"

        # Setup: NO worktree for the plan branch (only main worktree exists)
        # This simulates a remote-only PR with no local checkout
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", repo_dir=repo_dir),  # No plan branch worktree!
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=[plan_branch], commit_sha="abc123"),
                plan_branch: BranchMetadata.branch(plan_branch, "main", commit_sha="def456"),
            }
        )

        github_ops = FakeLocalGitHub(
            prs={
                plan_branch: PullRequestInfo(
                    number=100,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/100",
                    is_draft=False,
                    title="Fix something",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                100: PRDetails(
                    number=100,
                    url="https://github.com/owner/repo/pull/100",
                    title="Fix something",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name=plan_branch,
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={100: "main"},
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

        # Use FakeConsole with confirm_responses to auto-confirm any prompts
        fake_console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=True,
            is_stderr_tty=True,
            confirm_responses=[True, True, True],  # Confirm any prompts
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            console=fake_console,
            issues=issues_ops,
        )

        # Track if find_sessions_for_plan was called (it should NOT be called)
        find_sessions_called: list[str] = []

        def mock_find_sessions(repo_root, pr_id):
            find_sessions_called.append(pr_id)
            raise AssertionError(
                f"find_sessions_for_plan should NOT be called for remote PRs "
                f"(no local worktree), but was called with pr_id={pr_id}"
            )

        # Patch the method on the plan_backend instance
        monkeypatch.setattr(test_ctx.plan_backend, "find_sessions_for_plan", mock_find_sessions)

        # Execute mode: test PR merge with no local worktree
        # Note: worktree_path is None because there's no local checkout
        result = runner.invoke(
            cli,
            [
                "exec",
                "land-execute",
                "--pr-number=100",
                f"--branch={plan_branch}",
                # Note: NOT passing --worktree-path (no local worktree)
                "--use-graphite",
                "--script",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 100 in github_ops.merged_prs

        # CRITICAL: Verify find_sessions_for_plan was NOT called
        # because there's no local worktree to learn from
        assert len(find_sessions_called) == 0, (
            f"find_sessions_for_plan should not be called for remote PRs "
            f"(no local worktree to learn from), but was called {len(find_sessions_called)} times"
        )


def test_land_shows_learn_prompt_for_local_plan_branch() -> None:
    """Test that learn check is satisfied when plan has learn_status=completed_no_plan.

    With PlannedPRBackend, any branch that has a PR resolves to that PR as its plan.
    The learn check sees learn_status=completed_no_plan in the PR body and returns early,
    so find_sessions_for_plan is never called.

    This test verifies that the command succeeds without triggering session discovery.
    """
    from tests.fakes.gateway.console import FakeConsole

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Branch name follows old numeric pattern (no P prefix)
        plan_branch = "4867-fix-something"
        plan_worktree_path = repo_dir / "worktrees" / plan_branch

        # Setup: worktree EXISTS for the plan branch
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [plan_branch], repo_dir=repo_dir),
            current_branches={
                env.cwd: plan_branch,  # Currently on plan branch
                plan_worktree_path: plan_branch,  # Set current branch for worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, plan_worktree_path: env.git_dir},
            repository_roots={env.cwd: env.cwd, plan_worktree_path: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=[plan_branch], commit_sha="abc123"),
                plan_branch: BranchMetadata.branch(plan_branch, "main", commit_sha="def456"),
            }
        )

        from tests.test_utils.plan_helpers import format_plan_header_body_for_test

        github_ops = FakeLocalGitHub(
            prs={
                plan_branch: PullRequestInfo(
                    number=100,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/100",
                    is_draft=False,
                    title="Fix something",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                100: PRDetails(
                    number=100,
                    url="https://github.com/owner/repo/pull/100",
                    title="Fix something",
                    body=format_plan_header_body_for_test(learn_status="completed_no_plan"),
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name=plan_branch,
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={100: "main"},
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

        # Use FakeConsole with confirm_responses to auto-confirm any prompts
        fake_console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=True,
            is_stderr_tty=True,
            confirm_responses=[True, True, True],  # Confirm any prompts
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            console=fake_console,
            issues=issues_ops,
        )

        # Validation phase: test learn check passes because plan has learn_status=completed_no_plan
        result = runner.invoke(
            cli,
            ["land", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

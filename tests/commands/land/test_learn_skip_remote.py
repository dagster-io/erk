"""Tests for skipping learn prompt on remote PRs.

When landing a PR via `erk land <url>` or `erk land <number>` for a branch
that has NO local worktree, the learn status check should be skipped because
there are no local Claude sessions to learn from.

Regression test for issue #4871.
"""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands import land_cmd
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import PRDetails, PullRequestInfo
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
    """
    from erk_shared.gateway.console.fake import FakeConsole

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

        github_ops = FakeGitHub(
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
        # We do NOT use --force because that skips the learn check entirely
        # (we want to test that the worktree_path check prevents the call)
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
        find_sessions_called: list[int] = []

        def mock_find_sessions(github_issues, repo_root, plan_issue_number):
            find_sessions_called.append(plan_issue_number)
            raise AssertionError(
                f"find_sessions_for_plan should NOT be called for remote PRs "
                f"(no local worktree), but was called with plan_issue_number={plan_issue_number}"
            )

        # Patch the function in the land_cmd module
        monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

        # Land by URL - this is a remote PR with no local worktree
        # Don't use --force since that skips the learn check entirely
        result = runner.invoke(
            cli,
            ["land", "https://github.com/owner/repo/pull/100", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 100 in github_ops.merged_prs

        # CRITICAL: Verify find_sessions_for_plan was NOT called
        # because there's no local worktree to learn from
        assert len(find_sessions_called) == 0, (
            "find_sessions_for_plan should not be called for remote PRs "
            "(no local worktree to learn from)"
        )


def test_land_shows_learn_prompt_for_local_plan_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that learn prompt IS shown when landing a PR with a local worktree.

    When running `erk land` on a plan branch that HAS a local worktree, the learn
    status check should run because there may be local Claude sessions to learn from.

    This is the complementary test to ensure we didn't break the normal case.
    """
    from erk_shared.gateway.console.fake import FakeConsole

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Branch name follows plan pattern (starts with issue number)
        plan_branch = "4867-fix-something"

        # Setup: worktree EXISTS for the plan branch
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", [plan_branch], repo_dir=repo_dir),
            current_branches={env.cwd: plan_branch},  # Currently on plan branch
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

        github_ops = FakeGitHub(
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
        # We do NOT use --force because that skips the learn check entirely
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

        # Track if find_sessions_for_plan was called (it SHOULD be called)
        find_sessions_called: list[int] = []

        def mock_find_sessions(github_issues, repo_root, plan_issue_number):
            from erk_shared.sessions.discovery import SessionsForPlan

            find_sessions_called.append(plan_issue_number)
            # Return "already learned" so the command proceeds without prompting
            return SessionsForPlan(
                planning_session_id="plan-session-1",
                implementation_session_ids=["impl-session-1"],
                learn_session_ids=["learn-session-1"],  # Already learned
                last_remote_impl_at=None,
            )

        # Patch the function in the land_cmd module
        monkeypatch.setattr(land_cmd, "find_sessions_for_plan", mock_find_sessions)

        # Land from current branch (local worktree exists)
        # Don't use --force since that skips the learn check
        result = runner.invoke(
            cli,
            ["land", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 100 in github_ops.merged_prs

        # CRITICAL: Verify find_sessions_for_plan WAS called
        # because there's a local worktree that could have sessions
        assert len(find_sessions_called) == 1, (
            "find_sessions_for_plan should be called for local plan branches "
            f"(worktree exists), but was called {len(find_sessions_called)} times"
        )
        assert find_sessions_called[0] == 4867, (
            f"Expected plan_issue_number=4867, got {find_sessions_called[0]}"
        )

"""Tests for workflow smoke test core logic."""

from pathlib import Path

from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.tests.context import create_test_context

from erk.core.workflow_smoke_test import (
    SMOKE_TEST_BRANCH_PREFIX,
    SmokeTestError,
    SmokeTestResult,
    _extract_branch_name,
    cleanup_smoke_tests,
    run_smoke_test,
)
from erk_shared.context.context import ErkContext
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.types import PullRequestInfo, RepoInfo


class TestRunSmokeTest:
    def test_dispatches_through_production_one_shot_path(self) -> None:
        """Smoke test dispatches through dispatch_one_shot_remote production code path."""
        repo_root = Path("/fake/repo")
        git = FakeGit(
            git_common_dirs={repo_root: repo_root / ".git"},
            remote_urls={(repo_root, "origin"): "https://github.com/test-owner/test-repo.git"},
            default_branches={repo_root: "main"},
            current_branches={repo_root: "main"},
        )
        github = FakeLocalGitHub(
            authenticated=True,
            auth_username="testuser",
        )
        remote = FakeRemoteGitHub(
            authenticated_user="testuser",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-99",
            issues=None,
            issue_comments=None,
            pr_references=None,
        )

        ctx = ErkContext.for_test(
            git=git,
            github=github,
            remote_github=remote,
            repo_root=repo_root,
            repo_info=RepoInfo(owner="test-owner", name="test-repo"),
        )

        result = run_smoke_test(ctx, dispatch_ref=None)

        assert isinstance(result, SmokeTestResult)
        assert result.branch_name.startswith("plnd/smoke-test-")
        assert result.pr_number >= 1
        assert result.run_id  # non-empty
        assert result.run_url is not None
        assert "test-owner" in result.run_url

        # Verify branch was created via RemoteGitHub
        assert len(remote.created_refs) == 1
        ref = remote.created_refs[0]
        assert ref.ref.startswith("refs/heads/plnd/smoke-test-")

        # Verify commit was made
        assert len(remote.created_file_commits) == 1

        # Verify PR created with draft=True
        assert len(remote.created_pull_requests) == 1
        assert remote.created_pull_requests[0].draft is True

        # Verify PR body contains plan-header metadata (production path)
        assert "erk:metadata-block" in remote.created_pull_requests[0].body

        # Verify labels added
        assert len(remote.added_labels) == 1
        assert remote.added_labels[0].labels == ("erk-pr", "erk-plan")

        # Verify workflow triggered
        assert len(remote.dispatched_workflows) == 1
        wf = remote.dispatched_workflows[0]
        assert wf.workflow == "one-shot.yml"
        assert wf.inputs["submitted_by"] == "testuser"
        assert wf.inputs["plan_backend"] == "planned_pr"

    def test_returns_error_when_not_in_repo(self) -> None:
        """Smoke test returns error for NoRepoSentinel."""
        ctx = create_test_context(repo=NoRepoSentinel())

        result = run_smoke_test(ctx, dispatch_ref=None)

        assert isinstance(result, SmokeTestError)
        assert result.step == "validation"


class TestCleanupSmokeTests:
    def test_cleans_up_matching_branches(self) -> None:
        """Cleanup finds smoke test branches and closes PRs."""
        repo_root = Path("/fake/repo")
        git = FakeGit(
            git_common_dirs={repo_root: repo_root / ".git"},
            remote_urls={(repo_root, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={
                repo_root: [
                    "origin/main",
                    "origin/plnd/smoke-test-01-15-1430",
                    "origin/plnd/smoke-test-01-16-0900",
                    "origin/feature/unrelated",
                ],
            },
        )
        github = FakeLocalGitHub(
            prs={
                "plnd/smoke-test-01-15-1430": PullRequestInfo(
                    number=42,
                    title="One-shot: Add a code comment to any file.",
                    state="OPEN",
                    url="https://github.com/test-owner/test-repo/pull/42",
                    is_draft=True,
                    checks_passing=None,
                    owner="test-owner",
                    repo="test-repo",
                    head_branch="plnd/smoke-test-01-15-1430",
                ),
            },
        )

        ctx = ErkContext.for_test(
            git=git,
            github=github,
            repo_root=repo_root,
            repo_info=RepoInfo(owner="test-owner", name="test-repo"),
        )

        items = cleanup_smoke_tests(ctx)

        assert len(items) == 2

        # First item should have closed PR and deleted branch
        item_with_pr = next(i for i in items if i.pr_number == 42)
        assert item_with_pr.closed_pr is True
        assert item_with_pr.deleted_branch is True

        # Second item should have no PR
        item_without_pr = next(i for i in items if i.pr_number is None)
        assert item_without_pr.closed_pr is False
        assert item_without_pr.deleted_branch is True

        # Verify PRs were closed
        assert 42 in github.closed_prs

        # Verify remote branches deleted
        assert len(github.deleted_remote_branches) == 2

    def test_returns_empty_when_no_smoke_branches(self) -> None:
        """Cleanup returns empty list when no smoke branches exist."""
        repo_root = Path("/fake/repo")
        git = FakeGit(
            git_common_dirs={repo_root: repo_root / ".git"},
            remote_urls={(repo_root, "origin"): "https://github.com/test-owner/test-repo.git"},
            remote_branches={
                repo_root: ["origin/main", "origin/feature/unrelated"],
            },
        )
        github = FakeLocalGitHub()

        ctx = ErkContext.for_test(
            git=git,
            github=github,
            repo_root=repo_root,
            repo_info=RepoInfo(owner="test-owner", name="test-repo"),
        )

        items = cleanup_smoke_tests(ctx)

        assert items == []

    def test_returns_empty_for_no_repo_sentinel(self) -> None:
        """Cleanup returns empty for NoRepoSentinel."""
        ctx = create_test_context(repo=NoRepoSentinel())

        items = cleanup_smoke_tests(ctx)

        assert items == []


class TestExtractBranchName:
    def test_strips_origin_prefix(self) -> None:
        assert (
            _extract_branch_name("origin/plnd/smoke-test-01-15-1430")
            == "plnd/smoke-test-01-15-1430"
        )

    def test_strips_only_first_slash_segment(self) -> None:
        assert _extract_branch_name("origin/a/b/c") == "a/b/c"

    def test_returns_as_is_when_no_slash(self) -> None:
        assert _extract_branch_name("main") == "main"


class TestBranchPrefix:
    def test_smoke_test_branch_prefix_matches_plnd_pattern(self) -> None:
        """Branch prefix uses plnd/ production pattern."""
        assert SMOKE_TEST_BRANCH_PREFIX == "plnd/smoke-test-"

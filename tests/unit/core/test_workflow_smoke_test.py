"""Tests for workflow smoke test core logic."""

from pathlib import Path

from tests.fakes.context import create_test_context

from erk.core.workflow_smoke_test import (
    SmokeTestError,
    SmokeTestResult,
    _extract_branch_name,
    cleanup_smoke_tests,
    run_smoke_test,
)
from erk_shared.context.context import ErkContext
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PullRequestInfo, RepoInfo


class TestRunSmokeTest:
    def test_creates_branch_pr_and_triggers_workflow(self) -> None:
        """Smoke test dispatches branch, PR, and workflow in sequence."""
        repo_root = Path("/fake/repo")
        git = FakeGit(
            git_common_dirs={repo_root: repo_root / ".git"},
            remote_urls={(repo_root, "origin"): "https://github.com/test-owner/test-repo.git"},
            default_branches={repo_root: "main"},
        )
        github = FakeGitHub(
            authenticated=True,
            auth_username="testuser",
        )

        ctx = ErkContext.for_test(
            git=git,
            github=github,
            repo_root=repo_root,
            repo_info=RepoInfo(owner="test-owner", name="test-repo"),
        )

        result = run_smoke_test(ctx)

        assert isinstance(result, SmokeTestResult)
        assert result.branch_name.startswith("smoke-test/")
        assert result.pr_number >= 1
        assert result.run_id  # non-empty
        assert result.run_url is not None
        assert "test-owner" in result.run_url

        # Verify branch was created
        assert len(git.branch.created_branches) == 1
        created = git.branch.created_branches[0]
        assert created[1].startswith("smoke-test/")

        # Verify commit was made
        assert len(git.commit.branch_commits) == 1

        # Verify push
        assert len(git.remote.pushed_branches) == 1

        # Verify PR created with draft=True
        # created_prs is list of (branch, title, body, base, draft)
        assert len(github.created_prs) == 1
        _branch, _title, _body, _base, draft = github.created_prs[0]
        assert draft is True

        # Verify label was added
        assert len(github.added_labels) == 1
        assert github.added_labels[0] == (result.pr_number, "erk-plan")

        # Verify workflow triggered
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "one-shot.yml"
        assert inputs["branch_name"].startswith("smoke-test/")
        assert inputs["submitted_by"] == "testuser"

    def test_returns_error_when_not_in_repo(self) -> None:
        """Smoke test returns error for NoRepoSentinel."""
        ctx = create_test_context(repo=NoRepoSentinel())

        result = run_smoke_test(ctx)

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
                    "origin/smoke-test/01-15-1430",
                    "origin/smoke-test/01-16-0900",
                    "origin/feature/unrelated",
                ],
            },
        )
        github = FakeGitHub(
            prs={
                "smoke-test/01-15-1430": PullRequestInfo(
                    number=42,
                    title="Smoke test: 01-15-1430",
                    state="OPEN",
                    url="https://github.com/test-owner/test-repo/pull/42",
                    is_draft=True,
                    checks_passing=None,
                    owner="test-owner",
                    repo="test-repo",
                    head_branch="smoke-test/01-15-1430",
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
        github = FakeGitHub()

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
        assert _extract_branch_name("origin/smoke-test/01-15-1430") == "smoke-test/01-15-1430"

    def test_strips_only_first_slash_segment(self) -> None:
        assert _extract_branch_name("origin/a/b/c") == "a/b/c"

    def test_returns_as_is_when_no_slash(self) -> None:
        assert _extract_branch_name("main") == "main"

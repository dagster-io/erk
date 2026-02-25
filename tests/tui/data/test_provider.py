"""Tests for plan data provider."""

import json
from datetime import UTC, datetime
from pathlib import Path

from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.browser.fake import FakeBrowserLauncher
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PullRequestInfo,
)
from erk_shared.gateway.http.fake import FakeHttpClient
from erk_shared.gateway.plan_data_provider.real import RealPlanDataProvider
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.context import create_test_context
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _parse_header_fields(body: str) -> dict[str, object]:
    """Parse header_fields from a plan body for test Plan construction."""
    block = find_metadata_block(body, "plan-header")
    if block is None:
        return {}
    return dict(block.data)


def _make_repo_context(repo_root: Path, tmp_path: Path) -> RepoContext:
    """Create a RepoContext for testing."""
    erk_dir = tmp_path / ".erk"
    repo_dir = erk_dir / "repos" / "test-repo"
    return RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )


class TestBuildWorktreeMapping:
    """Tests for _build_worktree_mapping method."""

    def test_pool_managed_worktree_extracts_from_branch_name(self, tmp_path: Path) -> None:
        """Pool-managed worktree with P-prefix branch no longer extracts issue number.

        The directory name is 'erk-slot-02' (no issue prefix), and the branch name
        is 'P4280-add-required-kwargs-01-05-2230'. Since extract_leading_issue_number()
        always returns None, the branch cannot provide an issue number and the worktree
        is not added to the mapping.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create .erk directory to satisfy _ensure_erk_metadata_dir_from_context
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-02"
        branch_name = "P4280-add-required-kwargs-01-05-2230"

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Issue extraction from P-prefix branches no longer works
        assert 4280 not in mapping
        assert len(mapping) == 0

    def test_issue_named_worktree_extracts_from_branch_name(self, tmp_path: Path) -> None:
        """Issue-named worktree with P-prefix branch no longer extracts issue number.

        The directory name is 'P1234-feature-01-01-1200' (has issue prefix), and the
        branch name matches. Since extract_leading_issue_number() always returns None,
        the branch cannot provide an issue number and the worktree is not added to
        the mapping.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "P1234-feature-01-01-1200"
        branch_name = "P1234-feature-01-01-1200"

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Issue extraction from P-prefix branches no longer works
        assert 1234 not in mapping
        assert len(mapping) == 0

    def test_detached_head_worktree_not_in_mapping(self, tmp_path: Path) -> None:
        """Worktree with detached HEAD (branch=None) should not be in mapping."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        # Detached HEAD worktree has branch=None
        worktree_path = tmp_path / "worktrees" / "detached-wt"

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=None, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Detached HEAD should not produce an entry in mapping
        assert len(mapping) == 0

    def test_non_plan_branch_not_in_mapping(self, tmp_path: Path) -> None:
        """Worktree with non-P-prefixed branch should not be in mapping."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "feature-branch"

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-branch", is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Non-plan branch should not produce an entry
        assert len(mapping) == 0

    def test_planned_pr_branch_resolved_via_plan_ref_json(self, tmp_path: Path) -> None:
        """Draft PR branch (plnd/*) resolved via .impl/plan-ref.json.

        Branch name 'plnd/fix-missing-data-02-19-1416' doesn't contain a
        numeric issue prefix. The plan ID (PR number) comes from
        .impl/plan-ref.json inside the worktree directory.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-05"
        worktree_path.mkdir(parents=True)
        branch_name = "plnd/fix-missing-data-02-19-1416"

        # Create .impl/plan-ref.json on disk (read_plan_ref does direct I/O)
        impl_dir = worktree_path / ".impl"
        impl_dir.mkdir()
        plan_ref_data = {
            "provider": "github-draft-pr",
            "plan_id": "7624",
            "url": "https://github.com/test/repo/pull/7624",
            "created_at": "2026-02-19T14:16:00+00:00",
            "synced_at": "2026-02-19T14:16:00+00:00",
            "labels": ["erk-plan"],
            "objective_id": None,
        }
        (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref_data), encoding="utf-8")

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Plan ID 7624 should be extracted from .impl/plan-ref.json
        assert 7624 in mapping
        worktree_name, worktree_branch = mapping[7624]
        assert worktree_name == "erk-slot-05"
        assert worktree_branch == branch_name

    def test_legacy_planned_slash_branch_resolved_via_plan_ref_json(self, tmp_path: Path) -> None:
        """Legacy planned/ prefix branch resolved via .impl/plan-ref.json.

        Branch name 'planned/fix-auth-bug-01-15-1430' doesn't contain a
        numeric issue prefix. The plan ID comes from .impl/plan-ref.json.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-03"
        worktree_path.mkdir(parents=True)
        branch_name = "planned/fix-auth-bug-01-15-1430"

        # Create .impl/plan-ref.json on disk (read_plan_ref does direct I/O)
        impl_dir = worktree_path / ".impl"
        impl_dir.mkdir()
        plan_ref_data = {
            "provider": "github-draft-pr",
            "plan_id": "8001",
            "url": "https://github.com/test/repo/pull/8001",
            "created_at": "2026-01-15T14:30:00+00:00",
            "synced_at": "2026-01-15T14:30:00+00:00",
            "labels": ["erk-plan"],
            "objective_id": None,
        }
        (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref_data), encoding="utf-8")

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Plan ID 8001 should be extracted from .impl/plan-ref.json
        assert 8001 in mapping
        worktree_name, worktree_branch = mapping[8001]
        assert worktree_name == "erk-slot-03"
        assert worktree_branch == branch_name

    def test_planned_hyphen_branch_resolved_via_plan_ref_json(self, tmp_path: Path) -> None:
        """Branch with 'planned-' (hyphen) prefix resolved via plan-ref.json.

        After removing branch-name-based plan discovery, _build_worktree_mapping
        reads plan-ref.json from ALL worktrees regardless of branch name.
        Even non-standard branch names like 'planned-' (hyphen) work as long as
        plan-ref.json is present.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-04"
        worktree_path.mkdir(parents=True)
        branch_name = "planned-fix-auth-bug-01-15-1430"

        # Create .impl/plan-ref.json — will be read regardless of branch name format
        impl_dir = worktree_path / ".impl"
        impl_dir.mkdir()
        plan_ref_data = {
            "provider": "github-draft-pr",
            "plan_id": "9999",
            "url": "https://github.com/test/repo/pull/9999",
            "created_at": "2026-01-15T14:30:00+00:00",
            "synced_at": "2026-01-15T14:30:00+00:00",
            "labels": ["erk-plan"],
            "objective_id": None,
        }
        (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref_data), encoding="utf-8")

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Plan ID 9999 should be extracted from plan-ref.json regardless of branch name format
        assert 9999 in mapping
        worktree_name, worktree_branch = mapping[9999]
        assert worktree_name == "erk-slot-04"
        assert worktree_branch == branch_name

    def test_planned_pr_branch_without_plan_ref_not_in_mapping(self, tmp_path: Path) -> None:
        """Draft PR branch without .impl/plan-ref.json is not in mapping."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-05"
        worktree_path.mkdir(parents=True)
        branch_name = "plnd/fix-something-02-19-1416"

        # No .impl/plan-ref.json created

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # No plan-ref.json, so plnd/* branch should not produce an entry
        assert len(mapping) == 0


class TestClosePlan:
    """Tests for close_plan method using HTTP client."""

    def test_close_plan_uses_http_client(self, tmp_path: Path) -> None:
        """close_plan should use HTTP client to close issue via API."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        # Configure fake GitHub to return empty PR linkages
        from erk_shared.gateway.github.fake import FakeGitHub

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        http_client = FakeHttpClient()
        http_client.set_response(
            "repos/test/repo/issues/123",
            response={"state": "closed"},
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=http_client,
        )

        closed_prs = provider.close_plan(123, "https://github.com/test/repo/issues/123")

        # Verify HTTP client was used to close the issue
        assert len(http_client.requests) == 1
        request = http_client.requests[0]
        assert request.method == "PATCH"
        assert request.endpoint == "repos/test/repo/issues/123"
        assert request.data == {"state": "closed"}
        assert closed_prs == []

    def test_close_plan_closes_linked_prs(self, tmp_path: Path) -> None:
        """close_plan should close linked PRs before closing issue."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        # Configure fake GitHub to return linked PRs
        from erk_shared.gateway.github.fake import FakeGitHub
        from erk_shared.gateway.github.types import PullRequestInfo

        github = FakeGitHub(
            pr_issue_linkages={
                123: [
                    PullRequestInfo(
                        number=456,
                        state="OPEN",
                        url="https://github.com/test/repo/pulls/456",
                        is_draft=False,
                        title="Fix issue",
                        checks_passing=None,
                        owner="test",
                        repo="repo",
                    ),
                ],
            }
        )

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        http_client = FakeHttpClient()
        http_client.set_response(
            "repos/test/repo/pulls/456",
            response={"state": "closed"},
        )
        http_client.set_response(
            "repos/test/repo/issues/123",
            response={"state": "closed"},
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=http_client,
        )

        closed_prs = provider.close_plan(123, "https://github.com/test/repo/issues/123")

        # Verify HTTP client was used to close PR first, then issue
        assert len(http_client.requests) == 2
        assert http_client.requests[0].endpoint == "repos/test/repo/pulls/456"
        assert http_client.requests[1].endpoint == "repos/test/repo/issues/123"
        assert closed_prs == [456]

    def test_parse_owner_repo_from_url(self, tmp_path: Path) -> None:
        """_parse_owner_repo_from_url should extract owner/repo from URL."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        result = provider._parse_owner_repo_from_url("https://github.com/owner/repo/issues/123")
        assert result == ("owner", "repo")

        result = provider._parse_owner_repo_from_url("https://github.com/anthropic/erk/pulls/456")
        assert result == ("anthropic", "erk")

        # Invalid URL returns None
        result = provider._parse_owner_repo_from_url("invalid")
        assert result is None


class TestCommentCountsDisplay:
    """Tests for review comment counts display in _build_row_data.

    Comment counts are now fetched via the batched PR linkages GraphQL query
    and stored in PullRequestInfo.review_thread_counts as (resolved, total).
    """

    def test_comment_counts_from_pr_data(self, tmp_path: Path) -> None:
        """When PR has review_thread_counts, display as resolved/total."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Create test plan and PR linkage with comment counts
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )
        pr_linkages = {
            123: [
                PullRequestInfo(
                    number=456,
                    state="OPEN",
                    url="https://github.com/test/repo/pulls/456",
                    is_draft=False,
                    title="Fix issue",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                    review_thread_counts=(3, 5),  # 3 resolved out of 5 total
                ),
            ],
        }

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.resolved_comment_count == 3
        assert row.total_comment_count == 5
        assert row.comments_display == "3/5"

    def test_comment_counts_none_shows_zero(self, tmp_path: Path) -> None:
        """When PR has no review_thread_counts (None), display 0/0."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Create test plan and PR linkage without comment counts
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )
        pr_linkages = {
            123: [
                PullRequestInfo(
                    number=456,
                    state="OPEN",
                    url="https://github.com/test/repo/pulls/456",
                    is_draft=False,
                    title="Fix issue",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                    # review_thread_counts defaults to None
                ),
            ],
        }

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.resolved_comment_count == 0
        assert row.total_comment_count == 0
        assert row.comments_display == "0/0"

    def test_no_pr_shows_dash(self, tmp_path: Path) -> None:
        """When plan has no linked PR, display '-' for comments."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Create test plan without PR linkage
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )
        pr_linkages: dict[int, list[PullRequestInfo]] = {}  # No linked PRs

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.resolved_comment_count == 0
        assert row.total_comment_count == 0
        assert row.comments_display == "-"


class TestLearnStatusDisplay:
    """Tests for learn status display in _build_row_data."""

    def test_learn_status_none_shows_dash(self, tmp_path: Path) -> None:
        """When learn_status is None, display '-'."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan without learn_status metadata
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body="",  # No metadata block
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.learn_status is None
        assert row.learn_plan_issue is None
        assert row.learn_plan_pr is None
        assert row.learn_display == "- not started"

    def test_learn_status_pending_shows_spinner(self, tmp_path: Path) -> None:
        """When learn_status is 'pending', display spinner symbol."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: pending in metadata
        plan_body = format_plan_header_body_for_test(learn_status="pending")
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(plan_body),
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.learn_status == "pending"
        assert row.learn_display == "⟳ in progress"

    def test_learn_status_completed_no_plan_shows_empty_set(self, tmp_path: Path) -> None:
        """When learn_status is 'completed_no_plan', display empty set symbol."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_no_plan
        plan_body = format_plan_header_body_for_test(learn_status="completed_no_plan")
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(plan_body),
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.learn_status == "completed_no_plan"
        assert row.learn_display == "∅ no insights"

    def test_learn_status_completed_with_plan_shows_issue_number(self, tmp_path: Path) -> None:
        """When learn_status is 'completed_with_plan', display issue number."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_with_plan and learn_plan_issue
        plan_body = format_plan_header_body_for_test(
            learn_status="completed_with_plan", learn_plan_issue=456
        )
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(plan_body),
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        assert row.learn_plan_issue_closed is None
        assert row.learn_display == "📋 #456"

    def test_learn_status_plan_completed_shows_pr_number(self, tmp_path: Path) -> None:
        """When learn_status is 'plan_completed', display checkmark and PR number."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: plan_completed and learn_plan_pr
        plan_body = format_plan_header_body_for_test(
            learn_status="plan_completed", learn_plan_issue=456, learn_plan_pr=789
        )
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(plan_body),
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.learn_status == "plan_completed"
        assert row.learn_plan_issue == 456
        assert row.learn_plan_pr == 789
        assert row.learn_display == "✓ #789"

    def test_learn_status_completed_with_plan_closed_shows_checkmark(self, tmp_path: Path) -> None:
        """When learn plan issue is closed, display checkmark instead of clipboard."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_with_plan and learn_plan_issue
        plan_body = format_plan_header_body_for_test(
            learn_status="completed_with_plan", learn_plan_issue=456
        )
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(plan_body),
        )

        # Learn issue 456 is closed
        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={456: True},
        )

        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        assert row.learn_plan_issue_closed is True
        assert row.learn_display == "✅ #456"
        assert row.learn_display_icon == "✅ #456"

    def test_learn_status_completed_with_plan_open_shows_clipboard(self, tmp_path: Path) -> None:
        """When learn plan issue is open, display clipboard emoji."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        github = FakeGitHub(pr_issue_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_with_plan and learn_plan_issue
        plan_body = format_plan_header_body_for_test(
            learn_status="completed_with_plan", learn_plan_issue=456
        )
        plan = Plan(
            plan_identifier="123",
            title="Test Plan",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(plan_body),
        )

        # Learn issue 456 is open
        row = provider._build_row_data(
            plan=plan,
            plan_id=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={456: False},
        )

        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        assert row.learn_plan_issue_closed is False
        assert row.learn_display == "📋 #456"
        assert row.learn_display_icon == "📋 #456"


def _make_roadmap_body(steps_yaml: str) -> str:
    """Build a plan body with an objective-roadmap metadata block."""
    return (
        "# Objective: Test\n\n"
        "## Roadmap\n\n"
        "### Phase 1: Work\n\n"
        "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        "<!-- erk:metadata-block:objective-roadmap -->\n"
        "<details>\n"
        "<summary><code>objective-roadmap</code></summary>\n\n"
        "```yaml\n"
        "schema_version: '2'\n"
        "steps:\n"
        f"{steps_yaml}"
        "```\n\n"
        "</details>\n"
        "<!-- /erk:metadata-block:objective-roadmap -->\n"
    )


class TestBlockingDepsPlans:
    """Tests for blocking dependency plan collection in _build_row_data."""

    def _make_provider(self, tmp_path: Path) -> RealPlanDataProvider:
        """Create a minimal RealPlanDataProvider for testing."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        ctx = create_test_context(
            git=git,
            github=FakeGitHub(pr_issue_linkages={}),
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        return RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

    def test_no_blocking_deps_returns_empty(self, tmp_path: Path) -> None:
        """When next node has no non-terminal deps with plans, objective_head_plans is empty."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 is done, node 1.2 is pending and depends on 1.1 (terminal)
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: done\n"
            "  plan: '#100'\n"
            "  pr: null\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  plan: null\n"
            "  pr: null\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            plan_identifier="42",
            title="Objective: Test",
            body=body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.objective_head_plans == ()

    def test_blocking_dep_with_plan_collected(self, tmp_path: Path) -> None:
        """When next node has a non-terminal dep with a plan, it appears in objective_head_plans."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 is in_progress with a plan, node 1.2 depends on it and is pending
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  plan: '#100'\n"
            "  pr: null\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  plan: null\n"
            "  pr: null\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            plan_identifier="42",
            title="Objective: Test",
            body=body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert len(row.objective_head_plans) == 1
        display, url = row.objective_head_plans[0]
        assert display == "#100"
        assert url == "https://github.com/test/repo/issues/100"

    def test_blocking_dep_without_plan_not_collected(self, tmp_path: Path) -> None:
        """When next node has a non-terminal dep without a plan, it is not collected."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 is in_progress but has no plan
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  plan: null\n"
            "  pr: null\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  plan: null\n"
            "  pr: null\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            plan_identifier="42",
            title="Objective: Test",
            body=body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert row.objective_head_plans == ()

    def test_multiple_blocking_deps_collected(self, tmp_path: Path) -> None:
        """Multiple non-terminal deps with plans are all collected."""
        provider = self._make_provider(tmp_path)

        # Nodes 1.1 and 1.2 are in_progress with plans, node 1.3 depends on both
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  plan: '#100'\n"
            "  pr: null\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: in_progress\n"
            "  plan: '#200'\n"
            "  pr: null\n"
            "  depends_on: []\n"
            "- id: '1.3'\n"
            "  description: Third step\n"
            "  status: pending\n"
            "  plan: null\n"
            "  pr: null\n"
            "  depends_on: ['1.1', '1.2']\n"
        )

        plan = Plan(
            plan_identifier="42",
            title="Objective: Test",
            body=body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
        )

        row = provider._build_row_data(
            plan=plan,
            plan_id=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_plan_id={},
            use_graphite=False,
            learn_issue_states={},
        )

        assert len(row.objective_head_plans) == 2
        displays = [d for d, _url in row.objective_head_plans]
        assert "#100" in displays
        assert "#200" in displays


class TestFetchPlansByIds:
    """Tests for fetch_plans_by_ids method."""

    @staticmethod
    def _make_provider(
        tmp_path: Path,
        *,
        issues_data: list[IssueInfo] | None = None,
        pr_linkages: dict[int, list[PullRequestInfo]] | None = None,
    ) -> RealPlanDataProvider:
        repo_root = tmp_path / "repo"
        repo_root.mkdir(exist_ok=True)
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(exist_ok=True)

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )
        github = FakeGitHub(
            pr_issue_linkages=pr_linkages or {},
            issues_data=issues_data or [],
        )
        ctx = create_test_context(
            git=git,
            github=github,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )
        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        return RealPlanDataProvider(
            ctx=ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=FakeHttpClient(),
        )

    def test_empty_plan_ids_returns_empty(self, tmp_path: Path) -> None:
        """Empty plan_ids set returns empty list without API calls."""
        provider = self._make_provider(tmp_path)
        result = provider.fetch_plans_by_ids(set())
        assert result == []

    def test_fetches_matching_issues(self, tmp_path: Path) -> None:
        """Returns PlanRowData for each matching issue."""
        body = format_plan_header_body_for_test()
        issues = [
            IssueInfo(
                number=100,
                title="Plan: First",
                body=body,
                state="OPEN",
                url="https://github.com/test/repo/issues/100",
                labels=["erk-plan"],
                assignees=[],
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 2, tzinfo=UTC),
                author="testuser",
            ),
            IssueInfo(
                number=200,
                title="Plan: Second",
                body=body,
                state="CLOSED",
                url="https://github.com/test/repo/issues/200",
                labels=["erk-plan"],
                assignees=[],
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 2, tzinfo=UTC),
                author="testuser",
            ),
        ]
        provider = self._make_provider(tmp_path, issues_data=issues)
        result = provider.fetch_plans_by_ids({100, 200})

        assert len(result) == 2
        plan_ids = {r.plan_id for r in result}
        assert plan_ids == {100, 200}

    def test_results_sorted_by_plan_id(self, tmp_path: Path) -> None:
        """Results are sorted by plan_id ascending."""
        body = format_plan_header_body_for_test()
        issues = [
            IssueInfo(
                number=300,
                title="Plan: Third",
                body=body,
                state="OPEN",
                url="https://github.com/test/repo/issues/300",
                labels=["erk-plan"],
                assignees=[],
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 2, tzinfo=UTC),
                author="testuser",
            ),
            IssueInfo(
                number=100,
                title="Plan: First",
                body=body,
                state="OPEN",
                url="https://github.com/test/repo/issues/100",
                labels=["erk-plan"],
                assignees=[],
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 2, tzinfo=UTC),
                author="testuser",
            ),
        ]
        provider = self._make_provider(tmp_path, issues_data=issues)
        result = provider.fetch_plans_by_ids({100, 300})

        assert [r.plan_id for r in result] == [100, 300]

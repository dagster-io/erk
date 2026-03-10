"""Tests for plan data provider."""

import json
from datetime import UTC, datetime
from pathlib import Path

from erk.core.context import GlobalConfig
from erk.core.repo_discovery import RepoContext
from erk.tui.data.types import FetchTimings
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.gateway.plan_data_provider.real import RealPrDataProvider
from erk_shared.gateway.pr_service.real import RealPrService
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.browser import FakeBrowserLauncher
from tests.fakes.gateway.clipboard import FakeClipboard
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.graphite import FakeGraphite
from tests.fakes.gateway.http import FakeHttpClient
from tests.fakes.tests.context import create_test_context
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
        is 'P4280-add-required-kwargs-01-05-2230'. P-prefix branches cannot be resolved
        to plan IDs, so the worktree is not added to the mapping.
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Issue extraction from P-prefix branches no longer works
        assert 4280 not in mapping
        assert len(mapping) == 0

    def test_issue_named_worktree_extracts_from_branch_name(self, tmp_path: Path) -> None:
        """Issue-named worktree with P-prefix branch no longer extracts issue number.

        The directory name is 'P1234-feature-01-01-1200' (has issue prefix), and the
        branch name matches. P-prefix branches cannot be resolved to plan IDs, so
        the worktree is not added to the mapping.
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Non-plan branch should not produce an entry
        assert len(mapping) == 0

    def test_planned_pr_branch_resolved_via_plan_ref_json(self, tmp_path: Path) -> None:
        """Draft PR branch (plnd/*) resolved via branch-scoped .erk/impl-context/.

        Branch name 'plnd/fix-missing-data-02-19-1416' doesn't contain a
        numeric issue prefix. The plan ID (PR number) comes from
        .erk/impl-context/<branch>/plan-ref.json inside the worktree directory.
        """
        from erk_shared.impl_folder import get_impl_dir

        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-05"
        worktree_path.mkdir(parents=True)
        branch_name = "plnd/fix-missing-data-02-19-1416"

        # Create branch-scoped .erk/impl-context/<branch>/plan-ref.json on disk
        impl_dir = get_impl_dir(worktree_path, branch_name=branch_name)
        impl_dir.mkdir(parents=True, exist_ok=True)
        plan_ref_data = {
            "provider": "github-draft-pr",
            "plan_id": "7624",
            "url": "https://github.com/test/repo/pull/7624",
            "created_at": "2026-02-19T14:16:00+00:00",
            "synced_at": "2026-02-19T14:16:00+00:00",
            "labels": ["erk-pr"],
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
            current_branches={worktree_path: branch_name},
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Plan ID 7624 should be extracted from .impl/plan-ref.json
        assert 7624 in mapping
        worktree_name, worktree_branch = mapping[7624]
        assert worktree_name == "erk-slot-05"
        assert worktree_branch == branch_name

    def test_legacy_planned_slash_branch_resolved_via_plan_ref_json(self, tmp_path: Path) -> None:
        """Legacy planned/ prefix branch resolved via branch-scoped .erk/impl-context/.

        Branch name 'planned/fix-auth-bug-01-15-1430' doesn't contain a
        numeric issue prefix. The plan ID comes from .erk/impl-context/<branch>/plan-ref.json.
        """
        from erk_shared.impl_folder import get_impl_dir

        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-03"
        worktree_path.mkdir(parents=True)
        branch_name = "planned/fix-auth-bug-01-15-1430"

        # Create branch-scoped .erk/impl-context/<branch>/plan-ref.json on disk
        impl_dir = get_impl_dir(worktree_path, branch_name=branch_name)
        impl_dir.mkdir(parents=True, exist_ok=True)
        plan_ref_data = {
            "provider": "github-draft-pr",
            "plan_id": "8001",
            "url": "https://github.com/test/repo/pull/8001",
            "created_at": "2026-01-15T14:30:00+00:00",
            "synced_at": "2026-01-15T14:30:00+00:00",
            "labels": ["erk-pr"],
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
            current_branches={worktree_path: branch_name},
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Plan ID 8001 should be extracted from .impl/plan-ref.json
        assert 8001 in mapping
        worktree_name, worktree_branch = mapping[8001]
        assert worktree_name == "erk-slot-03"
        assert worktree_branch == branch_name

    def test_planned_hyphen_branch_resolved_via_plan_ref_json(self, tmp_path: Path) -> None:
        """Branch with non-standard name resolved via branch-scoped plan-ref.json.

        After removing branch-name-based plan discovery, _build_worktree_mapping
        reads plan-ref.json from branch-scoped .erk/impl-context/<branch>/ directories.
        Non-standard branch names like 'planned-' (hyphen) work as long as
        plan-ref.json is present in the correct branch-scoped location.
        """
        from erk_shared.impl_folder import get_impl_dir

        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-slot-04"
        worktree_path.mkdir(parents=True)
        branch_name = "planned-fix-auth-bug-01-15-1430"

        # Create branch-scoped plan-ref.json (works for non-standard branch names)
        impl_dir = get_impl_dir(worktree_path, branch_name=branch_name)
        impl_dir.mkdir(parents=True, exist_ok=True)
        plan_ref_data = {
            "provider": "github-draft-pr",
            "plan_id": "9999",
            "url": "https://github.com/test/repo/pull/9999",
            "created_at": "2026-01-15T14:30:00+00:00",
            "synced_at": "2026-01-15T14:30:00+00:00",
            "labels": ["erk-pr"],
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
            current_branches={worktree_path: branch_name},
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # Plan ID 9999 should be extracted from plan-ref.json regardless of branch name format
        assert 9999 in mapping
        worktree_name, worktree_branch = mapping[9999]
        assert worktree_name == "erk-slot-04"
        assert worktree_branch == branch_name

    def test_planned_pr_branch_without_plan_ref_not_in_mapping(self, tmp_path: Path) -> None:
        """Draft PR branch without branch-scoped plan-ref.json is not in mapping."""
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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        mapping = provider._build_worktree_mapping()

        # No plan-ref.json, so plnd/* branch should not produce an entry
        assert len(mapping) == 0


class TestClosePlan:
    """Tests for close_pr method using HTTP client."""

    def test_close_pr_uses_http_client(self, tmp_path: Path) -> None:
        """close_pr should use HTTP client to close issue via API."""
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
        from tests.fakes.gateway.github import FakeLocalGitHub

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        service = RealPrService(
            ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=http_client,
        )

        closed_prs = service.close_pr(123, "https://github.com/test/repo/issues/123")

        # Verify HTTP client was used to close the issue
        assert len(http_client.requests) == 1
        request = http_client.requests[0]
        assert request.method == "PATCH"
        assert request.endpoint == "repos/test/repo/issues/123"
        assert request.data == {"state": "closed"}
        assert closed_prs == []

    def test_close_pr_closes_linked_prs(self, tmp_path: Path) -> None:
        """close_pr should close linked PRs before closing issue."""
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
        from erk_shared.gateway.github.types import PullRequestInfo
        from tests.fakes.gateway.github import FakeLocalGitHub

        github = FakeLocalGitHub(
            pr_plan_linkages={
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
        service = RealPrService(
            ctx,
            location=location,
            clipboard=FakeClipboard(),
            browser=FakeBrowserLauncher(),
            http_client=http_client,
        )

        closed_prs = service.close_pr(123, "https://github.com/test/repo/issues/123")

        # Verify HTTP client was used to close PR first, then issue
        assert len(http_client.requests) == 2
        assert http_client.requests[0].endpoint == "repos/test/repo/pulls/456"
        assert http_client.requests[1].endpoint == "repos/test/repo/issues/123"
        assert closed_prs == [456]

    def test_parse_owner_repo_from_url(self) -> None:
        """_parse_owner_repo_from_url should extract owner/repo from URL."""
        from erk_shared.gateway.pr_service.real import _parse_owner_repo_from_url

        result = _parse_owner_repo_from_url("https://github.com/owner/repo/issues/123")
        assert result == ("owner", "repo")

        result = _parse_owner_repo_from_url("https://github.com/anthropic/erk/pulls/456")
        assert result == ("anthropic", "erk")

        # Invalid URL returns None
        result = _parse_owner_repo_from_url("invalid")
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Create test plan and PR linkage with comment counts
        plan = Plan(
            pr_identifier="123",
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
            pr_number=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Create test plan and PR linkage without comment counts
        plan = Plan(
            pr_identifier="123",
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
            pr_number=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Create test plan without PR linkage
        plan = Plan(
            pr_identifier="123",
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
            pr_number=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.resolved_comment_count == 0
        assert row.total_comment_count == 0
        assert row.comments_display == "-"


class TestStackedPrDetection:
    """Tests for stacked PR (🥞) detection in _build_row_data.

    Regression tests for the priority between Graphite's local parent data
    and GitHub's base_ref_name field when determining if a PR is stacked.
    """

    def test_graphite_parent_master_overrides_stale_github_base_ref(self, tmp_path: Path) -> None:
        """Graphite parent=main suppresses stacked indicator despite stale GitHub base_ref.

        Scenario: A child PR originally targeted a parent PR branch. The parent
        was merged and Graphite re-parented the child to main. But GitHub's
        base_ref_name still shows the old parent branch name (stale metadata).

        Old code checked GitHub first → saw stale base_ref → showed 🥞.
        New code checks Graphite first → sees parent=main → no 🥞.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        graphite = FakeGraphite()
        graphite.set_branch_parent("feature-child", "main")

        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            },
            git_common_dirs={repo_root: repo_root / ".git"},
        )

        global_config = GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            github_planning=True,
        )

        github = FakeLocalGitHub(pr_plan_linkages={})

        ctx = create_test_context(
            git=git,
            github=github,
            graphite=graphite,
            global_config=global_config,
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        plan = Plan(
            pr_identifier="123",
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
                    title="Fix child feature",
                    checks_passing=True,
                    owner="test",
                    repo="repo",
                    head_branch="feature-child",
                    base_ref_name="feature-parent",  # Stale GitHub metadata
                ),
            ],
        }

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages=pr_linkages,
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=True,
        )

        assert "🥞" not in row.status_display


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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan without learn_status metadata
        plan = Plan(
            pr_identifier="123",
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
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: pending in metadata
        pr_body = format_plan_header_body_for_test(learn_status="pending")
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_no_plan
        pr_body = format_plan_header_body_for_test(learn_status="completed_no_plan")
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_with_plan and learn_plan_issue
        pr_body = format_plan_header_body_for_test(
            learn_status="completed_with_plan", learn_plan_issue=456
        )
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: plan_completed and learn_plan_pr
        pr_body = format_plan_header_body_for_test(
            learn_status="plan_completed", learn_plan_issue=456, learn_plan_pr=789
        )
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_with_plan and learn_plan_issue
        pr_body = format_plan_header_body_for_test(
            learn_status="completed_with_plan", learn_plan_issue=456
        )
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        # learn_plan_issue_closed is always None (not fetched for perf)
        assert row.learn_plan_issue_closed is None
        assert row.learn_display == "📋 #456"
        assert row.learn_display_icon == "📋 #456"

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

        github = FakeLocalGitHub(pr_plan_linkages={})

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
        provider = RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

        # Plan with learn_status: completed_with_plan and learn_plan_issue
        pr_body = format_plan_header_body_for_test(
            learn_status="completed_with_plan", learn_plan_issue=456
        )
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        # learn_plan_issue_closed is always None (not fetched for perf)
        assert row.learn_plan_issue_closed is None
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

    def _make_provider(self, tmp_path: Path) -> RealPrDataProvider:
        """Create a minimal RealPrDataProvider for testing."""
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
            github=FakeLocalGitHub(pr_plan_linkages={}),
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        return RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

    def test_no_blocking_deps_returns_empty(self, tmp_path: Path) -> None:
        """When next node has no non-terminal deps with plans, objective_deps_plans is empty."""
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
            pr_identifier="42",
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
            pr_number=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.objective_deps_plans == ()

    def test_blocking_dep_with_plan_collected(self, tmp_path: Path) -> None:
        """When next node has a non-terminal dep with a plan, it appears in objective_deps_plans."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 is in_progress with a PR, node 1.2 depends on it and is pending
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  pr: '#100'\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  pr: null\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            pr_identifier="42",
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
            pr_number=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert len(row.objective_deps_plans) == 1
        display, url = row.objective_deps_plans[0]
        assert display == "#100"
        assert url == "https://github.com/test/repo/pull/100"

    def test_blocking_dep_without_pr_not_collected(self, tmp_path: Path) -> None:
        """When next node has a non-terminal dep without a PR, it is not collected."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 is in_progress but has no PR
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  pr: null\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  pr: null\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            pr_identifier="42",
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
            pr_number=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.objective_deps_plans == ()

    def test_multiple_blocking_deps_collected(self, tmp_path: Path) -> None:
        """Multiple non-terminal deps with plans are all collected."""
        provider = self._make_provider(tmp_path)

        # Nodes 1.1 and 1.2 are in_progress with PRs, node 1.3 depends on both
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  pr: '#100'\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: in_progress\n"
            "  pr: '#200'\n"
            "  depends_on: []\n"
            "- id: '1.3'\n"
            "  description: Third step\n"
            "  status: pending\n"
            "  pr: null\n"
            "  depends_on: ['1.1', '1.2']\n"
        )

        plan = Plan(
            pr_identifier="42",
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
            pr_number=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert len(row.objective_deps_plans) == 2
        displays = [d for d, _url in row.objective_deps_plans]
        assert "#100" in displays
        assert "#200" in displays

    def test_next_node_own_pr_collected(self, tmp_path: Path) -> None:
        """Node's own PR appears in objective_deps_plans when not terminal."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 is in_progress with its own PR, no deps
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  pr: '#300'\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  pr: null\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            pr_identifier="42",
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
            pr_number=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        # Node 1.1 is next (pending depends on it, but 1.1 is in_progress so
        # find_graph_next_node falls back to it). Its own PR should appear.
        assert len(row.objective_deps_plans) == 1
        display, url = row.objective_deps_plans[0]
        assert display == "#300"
        assert url == "https://github.com/test/repo/pull/300"

    def test_next_node_own_pr_not_duplicated_with_dep_pr(self, tmp_path: Path) -> None:
        """When next node's PR is also a blocking dep PR, it should not be duplicated."""
        provider = self._make_provider(tmp_path)

        # Node 1.1 has a PR and node 1.2 depends on it.
        # find_graph_next_node picks 1.2 (pending), and 1.1 is a blocking dep.
        # If 1.2 also happened to have the same PR (unusual but possible), no dupe.
        body = _make_roadmap_body(
            "- id: '1.1'\n"
            "  description: First step\n"
            "  status: in_progress\n"
            "  pr: '#400'\n"
            "  depends_on: []\n"
            "- id: '1.2'\n"
            "  description: Second step\n"
            "  status: pending\n"
            "  pr: '#400'\n"
            "  depends_on: ['1.1']\n"
        )

        plan = Plan(
            pr_identifier="42",
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
            pr_number=42,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        # #400 should appear only once (from blocking dep), not duplicated
        displays = [d for d, _url in row.objective_deps_plans]
        assert displays.count("#400") == 1


class TestPlanningRunIdFallback:
    """Tests for planning run ID fallback from created_from_workflow_run_url."""

    def _make_provider(self, tmp_path: Path) -> RealPrDataProvider:
        """Create a minimal RealPrDataProvider for testing."""
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
            github=FakeLocalGitHub(pr_plan_linkages={}),
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        return RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

    def test_planning_run_url_populates_run_fields(self, tmp_path: Path) -> None:
        """Planning run URL populates run_id and run_url when no dispatched run."""
        provider = self._make_provider(tmp_path)

        pr_body = format_plan_header_body_for_test(
            created_from_workflow_run_url="https://github.com/test/repo/actions/runs/12345678"
        )
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.run_id == "12345678"
        assert row.run_url == "https://github.com/test/repo/actions/runs/12345678"
        assert row.run_id_display == "12345678"
        assert row.run_status is None
        assert row.run_conclusion is None
        assert row.run_state_display == "-"

    def test_no_planning_run_url_shows_dash(self, tmp_path: Path) -> None:
        """Without planning run URL or dispatched run, run fields are defaults."""
        provider = self._make_provider(tmp_path)

        plan = Plan(
            pr_identifier="123",
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

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=None,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.run_id is None
        assert row.run_url is None
        assert row.run_id_display == "-"

    def test_dispatched_run_takes_precedence(self, tmp_path: Path) -> None:
        """When both dispatched run and planning run URL exist, dispatched run takes precedence."""
        provider = self._make_provider(tmp_path)

        pr_body = format_plan_header_body_for_test(
            created_from_workflow_run_url="https://github.com/test/repo/actions/runs/11111111"
        )
        plan = Plan(
            pr_identifier="123",
            title="Test Plan",
            body=pr_body,
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=[],
            assignees=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={},
            objective_id=None,
            header_fields=_parse_header_fields(pr_body),
        )

        workflow_run = WorkflowRun(
            run_id="99999999",
            status="completed",
            conclusion="success",
            branch="plnd/test",
            head_sha="abc123",
        )

        row = provider._build_row_data(
            plan=plan,
            pr_number=123,
            pr_linkages={},
            workflow_run=workflow_run,
            worktree_by_pr_number={},
            use_graphite=False,
        )

        assert row.run_id == "99999999"
        assert row.run_status == "completed"
        assert row.run_conclusion == "success"


class TestFetchPlansByIds:
    """Tests for fetch_prs_by_ids method."""

    @staticmethod
    def _make_provider(
        tmp_path: Path,
        *,
        issues_data: list[IssueInfo] | None = None,
        pr_linkages: dict[int, list[PullRequestInfo]] | None = None,
    ) -> RealPrDataProvider:
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
        github = FakeLocalGitHub(
            pr_plan_linkages=pr_linkages or {},
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
        return RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

    def test_empty_pr_ids_returns_empty(self, tmp_path: Path) -> None:
        """Empty pr_ids set returns empty list without API calls."""
        provider = self._make_provider(tmp_path)
        result = provider.fetch_prs_by_ids(set())
        assert result == []

    def test_fetches_matching_issues(self, tmp_path: Path) -> None:
        """Returns PrRowData for each matching issue."""
        body = format_plan_header_body_for_test()
        issues = [
            IssueInfo(
                number=100,
                title="Plan: First",
                body=body,
                state="OPEN",
                url="https://github.com/test/repo/issues/100",
                labels=["erk-pr"],
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
                labels=["erk-pr"],
                assignees=[],
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 2, tzinfo=UTC),
                author="testuser",
            ),
        ]
        provider = self._make_provider(tmp_path, issues_data=issues)
        result = provider.fetch_prs_by_ids({100, 200})

        assert len(result) == 2
        pr_ids = {r.pr_number for r in result}
        assert pr_ids == {100, 200}

    def test_results_sorted_by_pr_number(self, tmp_path: Path) -> None:
        """Results are sorted by pr_number ascending."""
        body = format_plan_header_body_for_test()
        issues = [
            IssueInfo(
                number=300,
                title="Plan: Third",
                body=body,
                state="OPEN",
                url="https://github.com/test/repo/issues/300",
                labels=["erk-pr"],
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
                labels=["erk-pr"],
                assignees=[],
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 2, tzinfo=UTC),
                author="testuser",
            ),
        ]
        provider = self._make_provider(tmp_path, issues_data=issues)
        result = provider.fetch_prs_by_ids({100, 300})

        assert [r.pr_number for r in result] == [100, 300]


class TestAppendTimingLog:
    """Tests for _append_timing_log method."""

    def _make_provider(self, tmp_path: Path) -> RealPrDataProvider:
        """Create a RealPrDataProvider for testing timing log."""
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
            github=FakeLocalGitHub(pr_plan_linkages={}),
            cwd=repo_root,
            repo=_make_repo_context(repo_root, tmp_path),
        )

        location = GitHubRepoLocation(
            root=repo_root,
            repo_id=GitHubRepoId(owner="test", repo="repo"),
        )
        return RealPrDataProvider(
            ctx=ctx,
            location=location,
            http_client=FakeHttpClient(),
        )

    def _make_timings(self) -> FetchTimings:
        return FetchTimings(
            rest_issues_ms=1000,
            graphql_enrich_ms=500,
            pr_parsing_ms=200,
            workflow_runs_ms=300,
            worktree_mapping_ms=50,
            row_building_ms=20,
            total_ms=2070,
        )

    def test_writes_timing_log_when_scratch_dir_exists(self, tmp_path: Path) -> None:
        """Appends a timing line when .erk/scratch/ directory exists."""
        provider = self._make_provider(tmp_path)
        scratch_dir = tmp_path / "repo" / ".erk" / "scratch"
        scratch_dir.mkdir()

        provider._append_timing_log(self._make_timings(), row_count=5)

        log_file = scratch_dir / "dash-timings.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "rows=5" in content
        assert "rest:1.0" in content

    def test_skips_when_scratch_dir_missing(self, tmp_path: Path) -> None:
        """Returns silently when .erk/scratch/ directory does not exist."""
        provider = self._make_provider(tmp_path)
        # Don't create scratch dir
        provider._append_timing_log(self._make_timings(), row_count=3)
        # Should not raise and no file created
        assert not (tmp_path / "repo" / ".erk" / "scratch" / "dash-timings.log").exists()

    def test_appends_multiple_entries(self, tmp_path: Path) -> None:
        """Multiple calls append separate lines to the log file."""
        provider = self._make_provider(tmp_path)
        scratch_dir = tmp_path / "repo" / ".erk" / "scratch"
        scratch_dir.mkdir()

        provider._append_timing_log(self._make_timings(), row_count=5)
        provider._append_timing_log(self._make_timings(), row_count=10)

        log_file = scratch_dir / "dash-timings.log"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "rows=5" in lines[0]
        assert "rows=10" in lines[1]

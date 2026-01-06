"""Tests for plan data provider."""

from pathlib import Path

from erk.core.repo_discovery import RepoContext
from erk.tui.data.provider import RealPlanDataProvider
from erk_shared.gateway.browser.fake import FakeBrowserLauncher
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.http.fake import FakeHttpClient
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation
from tests.fakes.context import create_test_context


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
        """Pool-managed worktree with generic directory name maps via branch.

        The directory name is 'erk-managed-wt-02' (no issue prefix),
        but the branch name is 'P4280-add-required-kwargs-01-05-2230',
        so issue 4280 should be extracted from the branch.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create .erk directory to satisfy _ensure_erk_metadata_dir_from_context
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()

        worktree_path = tmp_path / "worktrees" / "erk-managed-wt-02"
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

        # Issue 4280 should be extracted from the branch name
        assert 4280 in mapping
        worktree_name, worktree_branch = mapping[4280]
        assert worktree_name == "erk-managed-wt-02"
        assert worktree_branch == branch_name

    def test_issue_named_worktree_extracts_from_branch_name(self, tmp_path: Path) -> None:
        """Issue-named worktree with P-prefixed directory also extracts from branch.

        The directory name is 'P1234-feature-01-01-1200' (has issue prefix),
        and the branch name matches. Issue 1234 should be extracted from branch.
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

        # Issue 1234 should be extracted from the branch name
        assert 1234 in mapping
        worktree_name, worktree_branch = mapping[1234]
        assert worktree_name == "P1234-feature-01-01-1200"
        assert worktree_branch == branch_name

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
        from erk_shared.github.fake import FakeGitHub

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
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.types import PullRequestInfo

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

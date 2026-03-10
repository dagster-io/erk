"""Tests for fetch_pr_content on RealPrService."""

from pathlib import Path

from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.gateway.pr_service.real import RealPrService
from tests.fakes.gateway.browser import FakeBrowserLauncher
from tests.fakes.gateway.clipboard import FakeClipboard
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.http import FakeHttpClient
from tests.fakes.tests.context import create_test_context


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


def _make_service(tmp_path: Path, *, http_client: FakeHttpClient) -> RealPrService:
    """Create a RealPrService with minimal setup for testing."""
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

    return RealPrService(
        ctx,
        location=location,
        clipboard=FakeClipboard(),
        browser=FakeBrowserLauncher(),
        http_client=http_client,
    )


_WARNING = "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->"

BODY_WITH_PLAN_HEADER_METADATA = f"""{_WARNING}
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:30:00Z'
created_by: user123
plan_comment_id: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


def test_fetch_pr_content_returns_body_directly(tmp_path: Path) -> None:
    """Plan content without metadata block is returned directly."""
    http_client = FakeHttpClient()
    service = _make_service(tmp_path, http_client=http_client)

    plan_content = "# Draft PR Plan\n\nThis is the plan content."
    result = service.fetch_pr_content(42, plan_content)

    assert result == plan_content
    assert len(http_client.requests) == 0


def test_fetch_pr_content_empty_body_returns_none(tmp_path: Path) -> None:
    """Empty plan body returns None."""
    http_client = FakeHttpClient()
    service = _make_service(tmp_path, http_client=http_client)

    result = service.fetch_pr_content(42, "   ")

    assert result is None
    assert len(http_client.requests) == 0


def test_fetch_pr_content_with_embedded_metadata_returns_content(
    tmp_path: Path,
) -> None:
    """Plan body with embedded plan-header metadata returns the full body.

    This is the bug scenario from plan #8198: a PR body contains a plan-header
    metadata block (with null plan_comment_id). The old code returned None;
    the fix returns the body directly.
    """
    http_client = FakeHttpClient()
    service = _make_service(tmp_path, http_client=http_client)

    result = service.fetch_pr_content(123, BODY_WITH_PLAN_HEADER_METADATA)

    assert result == BODY_WITH_PLAN_HEADER_METADATA
    assert len(http_client.requests) == 0

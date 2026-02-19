"""Tests for fetch_plan_content on RealPlanDataProvider."""

from pathlib import Path

from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.browser.fake import FakeBrowserLauncher
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.metadata.plan_header import format_plan_content_comment
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from erk_shared.gateway.http.fake import FakeHttpClient
from erk_shared.gateway.plan_data_provider.real import RealPlanDataProvider
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


def _make_provider(tmp_path: Path, *, http_client: FakeHttpClient) -> RealPlanDataProvider:
    """Create a RealPlanDataProvider with minimal setup for testing."""
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

    return RealPlanDataProvider(
        ctx=ctx,
        location=location,
        clipboard=FakeClipboard(),
        browser=FakeBrowserLauncher(),
        http_client=http_client,
    )


_WARNING = "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->"

ISSUE_BODY_WITH_COMMENT_ID = f"""{_WARNING}
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:30:00Z'
created_by: user123
plan_comment_id: 99

```

</details>
<!-- /erk:metadata-block:plan-header -->"""

ISSUE_BODY_WITH_NULL_COMMENT_ID = f"""{_WARNING}
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


def test_fetch_plan_content_returns_content_from_comment(tmp_path: Path) -> None:
    """Happy path: issue body has plan_comment_id, HTTP returns comment with content."""
    http_client = FakeHttpClient()
    plan_content = "# My Plan\n\n1. Step one\n2. Step two"
    comment_body = format_plan_content_comment(plan_content)
    http_client.set_response(
        "repos/test/repo/issues/comments/99",
        response={"body": comment_body},
    )

    provider = _make_provider(tmp_path, http_client=http_client)
    result = provider.fetch_plan_content(123, ISSUE_BODY_WITH_COMMENT_ID)

    assert result is not None
    assert "# My Plan" in result
    assert "1. Step one" in result

    assert len(http_client.requests) == 1
    assert http_client.requests[0].endpoint == "repos/test/repo/issues/comments/99"


def test_fetch_plan_content_draft_pr_body_returned_directly(tmp_path: Path) -> None:
    """Draft PR plan: plan_body has no metadata block, returned directly without HTTP call."""
    http_client = FakeHttpClient()
    provider = _make_provider(tmp_path, http_client=http_client)

    plan_content = "# Draft PR Plan\n\nThis is the plan content."
    result = provider.fetch_plan_content(42, plan_content)

    assert result == plan_content
    assert len(http_client.requests) == 0


def test_fetch_plan_content_draft_pr_empty_body_returns_none(tmp_path: Path) -> None:
    """Draft PR plan with empty body returns None."""
    http_client = FakeHttpClient()
    provider = _make_provider(tmp_path, http_client=http_client)

    result = provider.fetch_plan_content(42, "   ")

    assert result is None
    assert len(http_client.requests) == 0


def test_fetch_plan_content_issue_body_missing_comment_id_returns_none(
    tmp_path: Path,
) -> None:
    """Issue body has plan-header block but null comment_id returns None."""
    http_client = FakeHttpClient()
    provider = _make_provider(tmp_path, http_client=http_client)

    result = provider.fetch_plan_content(123, ISSUE_BODY_WITH_NULL_COMMENT_ID)

    assert result is None
    assert len(http_client.requests) == 0

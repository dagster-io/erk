"""Integration tests for RealPrDataProvider.fetch_runs().

Tests the fetch_runs() method which aggregates workflow runs from
multiple registered workflows, deduplicates, links to PRs, and
builds RunRowData objects for the TUI Runs tab.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk.core.context import GlobalConfig
from erk.core.repo_discovery import RepoContext
from erk.tui.data.real_provider import RealPrDataProvider
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PullRequestInfo,
    WorkflowRun,
)
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.graphite import FakeGraphite
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


def _make_workflow_run(
    run_id: str,
    *,
    display_title: str | None = None,
    status: str = "completed",
    conclusion: str | None = "success",
    branch: str = "main",
    created_at: datetime | None = None,
    workflow_path: str = ".github/workflows/plan-implement.yml",
) -> WorkflowRun:
    """Create a WorkflowRun for testing."""
    return WorkflowRun(
        run_id=run_id,
        status=status,
        conclusion=conclusion,
        branch=branch,
        head_sha="abc123",
        display_title=display_title,
        created_at=created_at,
        workflow_path=workflow_path,
    )


def _make_provider(
    tmp_path: Path,
    *,
    workflow_runs: list[WorkflowRun] | None = None,
    pr_pr_linkages: dict[int, list[PullRequestInfo]] | None = None,
    prs: dict[str, PullRequestInfo] | None = None,
    pr_head_branches: dict[int, str] | None = None,
    use_graphite: bool = False,
) -> RealPrDataProvider:
    """Create a RealPrDataProvider wired to fakes for testing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir(exist_ok=True)
    erk_dir = repo_root / ".erk"
    erk_dir.mkdir(exist_ok=True)

    git = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    github = FakeLocalGitHub(
        workflow_runs=workflow_runs or [],
        pr_pr_linkages=pr_pr_linkages or {},
        prs=prs or {},
        pr_head_branches=pr_head_branches or {},
    )

    global_config = GlobalConfig.test(tmp_path / ".erk", use_graphite=use_graphite)

    ctx = create_test_context(
        git=git,
        github=github,
        graphite=FakeGraphite(),
        cwd=repo_root,
        global_config=global_config,
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


def test_fetch_runs_empty_when_no_workflow_runs(tmp_path: Path) -> None:
    """fetch_runs returns empty list when no workflow runs exist."""
    provider = _make_provider(tmp_path)
    rows = provider.fetch_runs()
    assert rows == []


def test_fetch_runs_returns_rows_for_workflow_runs(tmp_path: Path) -> None:
    """fetch_runs creates RunRowData for each workflow run."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="pr-address:#42:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
        _make_workflow_run(
            "1002",
            display_title="pr-address:#43:def456",
            created_at=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 2
    # Sorted by created_at descending
    assert rows[0].run_id == "1002"
    assert rows[1].run_id == "1001"


def test_fetch_runs_filters_to_known_workflows(tmp_path: Path) -> None:
    """fetch_runs only includes runs from known workflows in WORKFLOW_COMMAND_MAP."""
    known_run = _make_workflow_run(
        "1001",
        display_title="pr-address:#42:abc123",
        created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        workflow_path=".github/workflows/plan-implement.yml",
    )
    unknown_run = _make_workflow_run(
        "1002",
        display_title="unknown:abc123",
        created_at=datetime(2026, 3, 1, 11, 0, tzinfo=UTC),
        workflow_path=".github/workflows/unknown-workflow.yml",
    )
    provider = _make_provider(tmp_path, workflow_runs=[known_run, unknown_run])
    rows = provider.fetch_runs()

    # Only the known workflow run should appear
    assert len(rows) == 1
    assert rows[0].run_id == "1001"


def test_fetch_runs_extracts_pr_number_from_display_title(tmp_path: Path) -> None:
    """fetch_runs extracts PR number from display_title '#NNN' format."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="pr-address:#42:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs, pr_pr_linkages={})
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_number == 42
    assert rows[0].pr_display == "#42"


def test_fetch_runs_links_pr_number_runs_to_prs(tmp_path: Path) -> None:
    """fetch_runs links pr-number runs to their PRs via batch PR linkage."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="123:abc456",  # Legacy format: pr_number at start
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    pr = PullRequestInfo(
        number=99,
        state="OPEN",
        url="https://github.com/test/repo/pull/99",
        is_draft=False,
        title="Plan 123 implementation",
        checks_passing=True,
        owner="test",
        repo="repo",
    )
    provider = _make_provider(
        tmp_path,
        workflow_runs=runs,
        pr_pr_linkages={123: [pr]},
    )
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_number == 99
    assert rows[0].pr_display == "#99"
    assert rows[0].pr_url == "https://github.com/test/repo/pull/99"
    assert rows[0].title_display == "Plan 123 implementation"


def test_fetch_runs_run_url_format(tmp_path: Path) -> None:
    """fetch_runs builds correct GitHub Actions run URL."""
    runs = [
        _make_workflow_run(
            "1001",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].run_url == "https://github.com/test/repo/actions/runs/1001"


def test_fetch_runs_respects_max_display_limit(tmp_path: Path) -> None:
    """fetch_runs returns at most 50 runs."""
    runs = [
        _make_workflow_run(
            str(i),
            created_at=datetime(2026, 3, 1, i % 24, i % 60, tzinfo=UTC),
        )
        for i in range(60)
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) <= 50


def test_fetch_runs_sorted_by_created_at_descending(tmp_path: Path) -> None:
    """fetch_runs returns runs sorted most recent first."""
    runs = [
        _make_workflow_run(
            "oldest",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        _make_workflow_run(
            "newest",
            created_at=datetime(2026, 3, 1, tzinfo=UTC),
        ),
        _make_workflow_run(
            "middle",
            created_at=datetime(2026, 2, 1, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 3
    assert rows[0].run_id == "newest"
    assert rows[1].run_id == "middle"
    assert rows[2].run_id == "oldest"


def test_fetch_runs_no_pr_shows_dash_display(tmp_path: Path) -> None:
    """Runs without linked PRs show '-' for PR-related fields."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="some-branch:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_number is None
    assert rows[0].pr_url is None
    assert rows[0].pr_display == "-"
    assert rows[0].title_display == "-"


def test_fetch_runs_status_fields_populated(tmp_path: Path) -> None:
    """fetch_runs populates status and conclusion fields."""
    runs = [
        _make_workflow_run(
            "1001",
            status="completed",
            conclusion="failure",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].status == "completed"
    assert rows[0].conclusion == "failure"


def test_fetch_runs_in_progress_has_no_conclusion(tmp_path: Path) -> None:
    """In-progress runs have None conclusion."""
    runs = [
        _make_workflow_run(
            "1001",
            status="in_progress",
            conclusion=None,
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].status == "in_progress"
    assert rows[0].conclusion is None


def test_fetch_runs_pr_title_truncated_at_50_chars(tmp_path: Path) -> None:
    """PR titles longer than 50 chars are truncated with ellipsis."""
    long_title = "A" * 60
    runs = [
        _make_workflow_run(
            "1001",
            display_title="123:abc456",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    pr = PullRequestInfo(
        number=99,
        state="OPEN",
        url="https://github.com/test/repo/pull/99",
        is_draft=False,
        title=long_title,
        checks_passing=True,
        owner="test",
        repo="repo",
    )
    provider = _make_provider(
        tmp_path,
        workflow_runs=runs,
        pr_pr_linkages={123: [pr]},
    )
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert len(rows[0].title_display) == 50
    assert rows[0].title_display.endswith("...")


def test_fetch_runs_direct_pr_number_fetches_title_from_list_prs(tmp_path: Path) -> None:
    """Runs with PR number in display_title fetch title via list_prs."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="pr-address:#42:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    pr = PullRequestInfo(
        number=42,
        state="OPEN",
        url="https://github.com/test/repo/pull/42",
        is_draft=False,
        title="Fix auth bug",
        checks_passing=True,
        owner="test",
        repo="repo",
    )
    provider = _make_provider(
        tmp_path,
        workflow_runs=runs,
        prs={"fix-auth-bug": pr},
    )
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_number == 42
    assert rows[0].pr_display == "#42"
    assert rows[0].title_display == "Fix auth bug"
    assert rows[0].pr_title == "Fix auth bug"


def test_fetch_runs_pr_number_without_pr_details_shows_number_only(tmp_path: Path) -> None:
    """Runs with PR number from title but no open PR show just the number."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="pr-address:#42:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    # No prs and no PR linkages - PR details won't be found
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_number == 42
    assert rows[0].pr_display == "#42"
    assert rows[0].pr_url == "https://github.com/test/repo/pull/42"
    assert rows[0].title_display == "-"


def test_fetch_runs_branch_display_from_non_trunk_run_branch(tmp_path: Path) -> None:
    """fetch_runs uses run.branch when it's not master/main and no PR info."""
    runs = [
        _make_workflow_run(
            "1001",
            branch="feat/add-runs-tab",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].branch_display == "feat/add-runs-tab"


def test_fetch_runs_branch_display_dash_when_master_and_no_pr(tmp_path: Path) -> None:
    """fetch_runs shows '-' when run.branch is 'master' and no PR info available."""
    runs = [
        _make_workflow_run(
            "1001",
            branch="master",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].branch_display == "-"


def test_fetch_runs_branch_display_uses_pr_head_branch(tmp_path: Path) -> None:
    """fetch_runs uses PR's head_branch over run.branch when PR info available."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="pr-address:#42:abc123",
            branch="master",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    pr = PullRequestInfo(
        number=42,
        state="MERGED",
        url="https://github.com/test/repo/pull/42",
        is_draft=False,
        title="Fix auth bug",
        checks_passing=True,
        owner="test",
        repo="repo",
        head_branch="feat/fix-auth",
    )
    provider = _make_provider(tmp_path, workflow_runs=runs, prs={"feat/fix-auth": pr})
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].branch_display == "feat/fix-auth"


def test_fetch_runs_branch_display_truncated_at_40_chars(tmp_path: Path) -> None:
    """Branch names longer than 40 chars are truncated with ellipsis."""
    long_branch = "a" * 50
    runs = [
        _make_workflow_run(
            "1001",
            branch=long_branch,
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert len(rows[0].branch_display) == 40
    assert rows[0].branch_display.endswith("...")


def test_fetch_runs_pr_state_populated_from_pr_info(tmp_path: Path) -> None:
    """fetch_runs populates pr_state from pr_info.state when PR linked."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="pr-address:#42:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    pr = PullRequestInfo(
        number=42,
        state="MERGED",
        url="https://github.com/test/repo/pull/42",
        is_draft=False,
        title="Fix auth bug",
        checks_passing=True,
        owner="test",
        repo="repo",
    )
    provider = _make_provider(tmp_path, workflow_runs=runs, prs={"feat/fix-auth": pr})
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_state == "MERGED"


def test_fetch_runs_pr_state_none_when_no_pr(tmp_path: Path) -> None:
    """fetch_runs sets pr_state to None when no PR is linked."""
    runs = [
        _make_workflow_run(
            "1001",
            display_title="some-branch:abc123",
            created_at=datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        ),
    ]
    provider = _make_provider(tmp_path, workflow_runs=runs)
    rows = provider.fetch_runs()

    assert len(rows) == 1
    assert rows[0].pr_state is None

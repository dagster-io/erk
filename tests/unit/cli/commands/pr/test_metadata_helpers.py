"""Unit tests for plan dispatch metadata helpers."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.metadata_helpers import (
    maybe_update_plan_dispatch_metadata,
    write_dispatch_metadata,
)
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.plan_store.planned_pr import ManagedGitHubPrBackend
from tests.commands.dispatch.conftest import create_plan, make_plan_body
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.time import FakeTime
from tests.test_utils.plan_helpers import create_plan_store_with_plans
from tests.test_utils.test_context import context_for_test


def _register_branch_alias(fake_github: FakeLocalGitHub, pr_id: str, branch: str) -> None:
    """Register an additional branch name for an existing PR in FakeLocalGitHub.

    ManagedGitHubPrBackend resolves plans via get_pr_for_branch, which requires
    the PR to be registered under the actual branch name.
    """
    synthetic_branch = f"plan-{pr_id}"
    fake_github._prs[branch] = fake_github._prs[synthetic_branch]
    fake_github._prs_by_branch[branch] = fake_github._pr_details[int(pr_id)]


def _make_repo(tmp_path: Path) -> RepoContext:
    """Create a minimal RepoContext for testing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    return RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )


def _create_backend_with_raw_body(
    pr_number: int,
    body: str,
    *,
    branch: str = "",
    author: str = "test-author",
) -> tuple[ManagedGitHubPrBackend, FakeLocalGitHub]:
    """Create ManagedGitHubPrBackend with a PR that has the exact given body (no auto-synthesis).

    This bypasses create_plan_store_with_plans which auto-synthesizes a plan-header
    when the body doesn't contain one. Use this to test ensure_plan_header on PRs
    that genuinely lack a plan-header block.
    """
    if not branch:
        branch = f"plan-{pr_number}"
    pr_details = PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title="Test plan",
        body=body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        author=author,
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
    )
    prs = {
        branch: PullRequestInfo(
            number=pr_number,
            state="OPEN",
            url=pr_details.url,
            is_draft=True,
            title=pr_details.title,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
            head_branch=branch,
        ),
    }
    fake_github = FakeLocalGitHub(
        pr_details={pr_number: pr_details},
        prs=prs,
    )
    backend = ManagedGitHubPrBackend(fake_github, fake_github.issues, time=FakeTime())
    return backend, fake_github


# --- Tests for maybe_update_plan_dispatch_metadata ---


class _FakeGitHubNoNodeId(FakeLocalGitHub):
    """FakeLocalGitHub that returns None for node_id lookups."""

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> None:
        return None


def test_update_non_plan_branch_skips_update(tmp_path: Path) -> None:
    """Branch without P{number} prefix causes early return with no metadata update."""
    repo = _make_repo(tmp_path)
    plan = create_plan("123", "Test plan")
    plan_store, fake_github = create_plan_store_with_plans({"123": plan})
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo)

    maybe_update_plan_dispatch_metadata(ctx, repo, "feature-branch", "run-99")

    assert fake_github.updated_pr_bodies == []


def test_update_missing_node_id_skips_update(tmp_path: Path) -> None:
    """Run ID exists but node_id fetch returns None — skips metadata update."""
    repo = _make_repo(tmp_path)
    plan = create_plan("456", "Test plan", body=make_plan_body())
    plan_store, fake_github = create_plan_store_with_plans({"456": plan})
    _register_branch_alias(fake_github, "456", "P456-fix-bug")
    ctx = context_for_test(
        cwd=repo.root,
        plan_store=plan_store,
        repo=repo,
        github=_FakeGitHubNoNodeId(),
    )

    maybe_update_plan_dispatch_metadata(ctx, repo, "P456-fix-bug", "run-99")

    assert fake_github.updated_pr_bodies == []


def test_update_successful_writes_metadata(tmp_path: Path) -> None:
    """Happy path: all guards pass, metadata written with run_id, node_id, timestamp."""
    fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    fake_time = FakeTime(current_time=fixed_time)
    repo = _make_repo(tmp_path)
    plan = create_plan("321", "Test plan", body=make_plan_body())
    plan_store, fake_github = create_plan_store_with_plans({"321": plan})
    _register_branch_alias(fake_github, "321", "P321-fix-bug")
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo, time=fake_time)

    maybe_update_plan_dispatch_metadata(ctx, repo, "P321-fix-bug", "run-42")

    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "last_dispatched_run_id: run-42" in updated_body
    assert "last_dispatched_node_id: WFR_fake_node_id_run-42" in updated_body
    assert "2024-06-15T12:00:00+00:00" in updated_body


# --- Tests for ensure_plan_header ---


def test_ensure_plan_header_noop_when_exists(tmp_path: Path) -> None:
    """PR with existing plan-header is unchanged by ensure_plan_header."""
    repo = _make_repo(tmp_path)
    plan = create_plan("100", "Test plan", body=make_plan_body())
    plan_store, fake_github = create_plan_store_with_plans({"100": plan})

    plan_store.ensure_plan_header(repo.root, "100")

    # No body update should have been made (the header already exists)
    assert fake_github.updated_pr_bodies == []


def test_ensure_plan_header_creates_when_missing(tmp_path: Path) -> None:
    """PR with no plan-header gets one created by ensure_plan_header."""
    repo = _make_repo(tmp_path)
    raw_body = "# Plan\n\nImplementation details..."
    plan_store, fake_github = _create_backend_with_raw_body(200, raw_body)

    plan_store.ensure_plan_header(repo.root, "200")

    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["schema_version"] == "2"
    assert block.data["created_at"] == "2024-01-15T10:30:00+00:00"
    assert block.data["created_by"] == "test-author"


# --- Tests for write_dispatch_metadata with missing plan-header ---


def test_write_dispatch_metadata_succeeds_without_plan_header(tmp_path: Path) -> None:
    """write_dispatch_metadata auto-creates plan-header when missing."""
    repo = _make_repo(tmp_path)
    raw_body = "# Plan\n\nImplementation details..."
    plan_store, fake_github = _create_backend_with_raw_body(300, raw_body)

    write_dispatch_metadata(
        plan_backend=plan_store,
        github=fake_github,
        repo_root=repo.root,
        pr_number=300,
        run_id="run-55",
        dispatched_at="2024-06-15T12:00:00+00:00",
    )

    # Should have two body updates: one for ensure_plan_header, one for update_metadata
    assert len(fake_github.updated_pr_bodies) == 2
    _, final_body = fake_github.updated_pr_bodies[-1]
    assert "last_dispatched_run_id: run-55" in final_body


# --- Tests for maybe_update with missing plan-header ---


def test_maybe_update_creates_header_when_missing(tmp_path: Path) -> None:
    """maybe_update_plan_dispatch_metadata creates header when missing (instead of skipping)."""
    fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    fake_time = FakeTime(current_time=fixed_time)
    repo = _make_repo(tmp_path)
    branch = "P400-fix-bug"
    raw_body = "# Plan\n\nImplementation details..."
    plan_store, fake_github = _create_backend_with_raw_body(400, raw_body, branch=branch)
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo, time=fake_time)

    maybe_update_plan_dispatch_metadata(ctx, repo, branch, "run-77")

    # Should have body updates: ensure_plan_header + update_metadata
    assert len(fake_github.updated_pr_bodies) >= 2
    _, final_body = fake_github.updated_pr_bodies[-1]
    assert "last_dispatched_run_id: run-77" in final_body
    block = find_metadata_block(final_body, "plan-header")
    assert block is not None

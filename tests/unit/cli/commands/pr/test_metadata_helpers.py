"""Unit tests for maybe_write_pending_dispatch_metadata."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.metadata_helpers import maybe_write_pending_dispatch_metadata
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.time.fake import FakeTime
from tests.commands.submit.conftest import create_plan, make_plan_body
from tests.test_utils.plan_helpers import create_plan_store_with_plans


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


def test_non_plan_branch_skips_metadata_write(tmp_path: Path) -> None:
    """Branch without P{number} prefix causes early return with no metadata write."""
    repo = _make_repo(tmp_path)
    plan = create_plan("123", "Test plan")
    plan_store, fake_issues = create_plan_store_with_plans({"123": plan})
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo)

    maybe_write_pending_dispatch_metadata(ctx, repo, "feature-branch")

    assert fake_issues.updated_bodies == []


def test_plan_branch_without_metadata_block_skips_write(tmp_path: Path) -> None:
    """Plan branch where issue lacks a plan-header block causes early return."""
    repo = _make_repo(tmp_path)
    plan = create_plan("456", "Test plan", body="Just a plain description")
    plan_store, fake_issues = create_plan_store_with_plans({"456": plan})
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo)

    maybe_write_pending_dispatch_metadata(ctx, repo, "P456-fix-bug")

    assert fake_issues.updated_bodies == []


def test_plan_branch_with_metadata_block_writes_pending_marker(tmp_path: Path) -> None:
    """Plan branch with plan-header block writes pending dispatch sentinel."""
    fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    fake_time = FakeTime(current_time=fixed_time)
    repo = _make_repo(tmp_path)
    plan = create_plan("789", "Test plan", body=make_plan_body())
    plan_store, fake_issues = create_plan_store_with_plans({"789": plan})
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo, time=fake_time)

    maybe_write_pending_dispatch_metadata(ctx, repo, "P789-fix-bug")

    assert len(fake_issues.updated_bodies) == 1
    _, updated_body = fake_issues.updated_bodies[0]
    assert "last_dispatched_run_id: null" in updated_body
    assert "last_dispatched_node_id: null" in updated_body
    assert "2024-06-15T12:00:00+00:00" in updated_body

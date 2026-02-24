"""Unit tests for plan dispatch metadata helpers."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.metadata_helpers import (
    maybe_update_plan_dispatch_metadata,
    maybe_write_pending_dispatch_metadata,
)
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.time.fake import FakeTime
from tests.commands.submit.conftest import create_plan, make_plan_body
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _register_branch_alias(fake_github: FakeGitHub, plan_id: str, branch: str) -> None:
    """Register an additional branch name for an existing PR in FakeGitHub.

    PlannedPRBackend resolves plans via get_pr_for_branch, which requires
    the PR to be registered under the actual branch name.
    """
    synthetic_branch = f"plan-{plan_id}"
    fake_github._prs[branch] = fake_github._prs[synthetic_branch]
    fake_github._prs_by_branch[branch] = fake_github._pr_details[int(plan_id)]


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
    plan_store, fake_github = create_plan_store_with_plans({"123": plan})
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo)

    maybe_write_pending_dispatch_metadata(ctx, repo, "feature-branch")

    assert fake_github.updated_pr_bodies == []


def test_plan_branch_with_metadata_block_writes_pending_marker(tmp_path: Path) -> None:
    """Plan branch with plan-header block writes pending dispatch sentinel."""
    fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    fake_time = FakeTime(current_time=fixed_time)
    repo = _make_repo(tmp_path)
    plan = create_plan("789", "Test plan", body=make_plan_body())
    plan_store, fake_github = create_plan_store_with_plans({"789": plan})
    _register_branch_alias(fake_github, "789", "P789-fix-bug")
    ctx = context_for_test(cwd=repo.root, plan_store=plan_store, repo=repo, time=fake_time)

    maybe_write_pending_dispatch_metadata(ctx, repo, "P789-fix-bug")

    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "last_dispatched_run_id: null" in updated_body
    assert "last_dispatched_node_id: null" in updated_body
    assert "2024-06-15T12:00:00+00:00" in updated_body


# --- Tests for maybe_update_plan_dispatch_metadata ---


class _FakeGitHubNoNodeId(FakeGitHub):
    """FakeGitHub that returns None for node_id lookups."""

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

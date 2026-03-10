"""Shared fixtures and helpers for dispatch command tests."""

from datetime import UTC, datetime
from pathlib import Path

from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.types import MetadataBlock
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.test_context import context_for_test


def make_plan_body(content: str = "Implementation details...") -> str:
    """Create a valid issue body with plan-header metadata block.

    The plan-header block is required for `update_plan_header_dispatch` to work.
    """
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Plan\n\n{content}"


def create_plan(
    plan_identifier: str,
    title: str,
    body: str | None = None,
    state: PlanState = PlanState.OPEN,
    labels: list[str] | None = None,
) -> Plan:
    """Create a Plan with common defaults for testing."""
    now = datetime.now(UTC)
    return Plan(
        pr_identifier=plan_identifier,
        title=title,
        body=body if body is not None else make_plan_body(),
        state=state,
        url=f"https://github.com/test-owner/test-repo/issues/{plan_identifier}",
        labels=labels if labels is not None else ["erk-pr"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
        objective_id=None,
    )


def setup_submit_context(
    tmp_path: Path,
    plans: dict[str, Plan],
    git_kwargs: dict | None = None,
    github_kwargs: dict | None = None,
    graphite_kwargs: dict | None = None,
    *,
    use_graphite: bool = False,
    confirm_responses: list[bool] | None = None,
    remote_branch_refs: list[str] | None = None,
):
    """Setup common context for submit tests.

    Args:
        use_graphite: If True, enable Graphite integration (allows track_branch calls).
                     Default False for backwards compatibility with existing tests.
        confirm_responses: List of boolean responses for ctx.console.confirm() calls.
                          If None, uses default FakeConsole with no responses configured.
        remote_branch_refs: List of remote branch refs (e.g., ["origin/branch", "origin/master"]).
                           These are passed to FakeGit's remote_branches keyed by repo_root.

    Returns (ctx, fake_git, fake_github, fake_backing, fake_graphite, repo_root)
        where fake_backing is FakeLocalGitHub.
    """
    from erk_shared.context.types import GlobalConfig
    from tests.fakes.gateway.console import FakeConsole
    from tests.fakes.gateway.git import FakeGit
    from tests.fakes.gateway.github import FakeLocalGitHub
    from tests.fakes.gateway.graphite import FakeGraphite
    from tests.test_utils.plan_helpers import create_plan_store_with_plans

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_plan_store, fake_backing = create_plan_store_with_plans(plans)

    git_kwargs = git_kwargs or {}
    if "current_branches" not in git_kwargs:
        git_kwargs["current_branches"] = {repo_root: "main"}
    if "trunk_branches" not in git_kwargs:
        git_kwargs["trunk_branches"] = {repo_root: "master"}
    if remote_branch_refs is not None:
        git_kwargs["remote_branches"] = {repo_root: remote_branch_refs}

    fake_git = FakeGit(**git_kwargs)
    fake_github = FakeLocalGitHub(**(github_kwargs or {}))
    # When use_graphite=False, use GraphiteDisabled sentinel to match production behavior
    if use_graphite:
        fake_graphite = FakeGraphite(**(graphite_kwargs or {}))
    else:
        from erk_shared.gateway.graphite.disabled import (
            GraphiteDisabled,
            GraphiteDisabledReason,
        )

        fake_graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )

    # Create GlobalConfig with use_graphite setting
    global_config = GlobalConfig.test(erk_root=repo_dir, use_graphite=use_graphite)

    # Create FakeConsole with confirm responses if provided
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=confirm_responses,
    )

    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_backing.issues,
        plan_store=fake_plan_store,
        graphite=fake_graphite,
        repo=repo,
        global_config=global_config,
        console=fake_console,
    )

    return ctx, fake_git, fake_github, fake_backing, fake_graphite, repo_root

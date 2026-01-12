"""Shared fixtures and helpers for submit command tests."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.submit import ERK_PLAN_LABEL
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.github.metadata.core import render_metadata_block
from erk_shared.github.metadata.types import MetadataBlock
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.plan_helpers import create_plan_store_with_plans


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


def make_learn_plan_body(content: str = "Documentation learning...") -> str:
    """Create a valid learn plan issue body with plan-header metadata block.

    Note: Learn plans are identified by the erk-learn label, not by metadata fields.
    """
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Learn Plan\n\n{content}"


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
        plan_identifier=plan_identifier,
        title=title,
        body=body if body is not None else make_plan_body(),
        state=state,
        url=f"https://github.com/test-owner/test-repo/issues/{plan_identifier}",
        labels=labels if labels is not None else [ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
    )


def setup_submit_context(
    tmp_path: Path,
    plans: dict[str, Plan],
    git_kwargs: dict | None = None,
    github_kwargs: dict | None = None,
    issues_kwargs: dict | None = None,
    graphite_kwargs: dict | None = None,
    *,
    use_graphite: bool = False,
):
    """Setup common context for submit tests.

    Args:
        use_graphite: If True, enable Graphite integration (allows track_branch calls).
                     Default False for backwards compatibility with existing tests.

    Returns (ctx, fake_git, fake_github, fake_github_issues, fake_graphite, repo_root)
    """
    from erk_shared.context.types import GlobalConfig
    from erk_shared.gateway.graphite.fake import FakeGraphite
    from erk_shared.git.fake import FakeGit
    from erk_shared.github.fake import FakeGitHub

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_plan_store, fake_github_issues = create_plan_store_with_plans(plans)

    git_kwargs = git_kwargs or {}
    if "current_branches" not in git_kwargs:
        git_kwargs["current_branches"] = {repo_root: "main"}
    if "trunk_branches" not in git_kwargs:
        git_kwargs["trunk_branches"] = {repo_root: "master"}

    fake_git = FakeGit(**git_kwargs)
    fake_github = FakeGitHub(**(github_kwargs or {}))
    fake_graphite = FakeGraphite(**(graphite_kwargs or {}))

    # Update issues kwargs if provided
    if issues_kwargs:
        for key, value in issues_kwargs.items():
            setattr(fake_github_issues, f"_{key}", value)

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

    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        graphite=fake_graphite,
        repo=repo,
        global_config=global_config,
    )

    return ctx, fake_git, fake_github, fake_github_issues, fake_graphite, repo_root

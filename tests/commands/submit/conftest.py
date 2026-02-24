"""Shared fixtures and helpers for submit command tests."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.submit import ERK_PLAN_LABEL
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.types import MetadataBlock
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.plan_helpers import create_plan_store


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
        objective_id=None,
    )


def create_pr_details_for_plan(
    plan: Plan,
    branch_name: str,
    base_branch: str = "main",
) -> "PRDetails":
    """Create PRDetails for a planned-PR plan.

    Args:
        plan: The Plan object
        branch_name: The branch name for the PR
        base_branch: The base branch for the PR

    Returns:
        PRDetails with plan body and erk-plan label
    """
    from erk_shared.gateway.github.types import PRDetails

    return PRDetails(
        number=int(plan.plan_identifier),
        url=plan.url,
        title=plan.title,
        body=plan.body,
        state="OPEN",
        is_draft=True,
        base_ref_name=base_branch,
        head_ref_name=branch_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=tuple(plan.labels),
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
    confirm_responses: list[bool] | None = None,
    remote_branch_refs: list[str] | None = None,
    backend: str = "planned_pr",
    pr_details_map: dict[int, "PRDetails"] | None = None,
    issues: "FakeGitHubIssues | None" = None,
):
    """Setup common context for submit tests.

    Args:
        use_graphite: If True, enable Graphite integration (allows track_branch calls).
                     Default False for backwards compatibility with existing tests.
        confirm_responses: List of boolean responses for ctx.console.confirm() calls.
                          If None, uses default FakeConsole with no responses configured.
        remote_branch_refs: List of remote branch refs (e.g., ["origin/branch", "origin/master"]).
                           These are passed to FakeGit's remote_branches keyed by repo_root.
        backend: Plan store backend type - "github" or "planned_pr" (default: "planned_pr").
        pr_details_map: For planned_pr backend, mapping of PR number -> PRDetails.
                       If None, PRDetails are auto-generated from plans using plnd/ branch naming.
        issues: Optional pre-built FakeGitHubIssues for ctx.issues. Useful when the
                submit flow needs issue data (e.g., learn plan detection) even with
                planned_pr backend.

    Returns (ctx, fake_git, fake_github, fake_backing, fake_graphite, repo_root)
        where fake_backing is FakeGitHubIssues (github) or FakeGitHub (planned_pr).
    """
    from erk_shared.context.types import GlobalConfig
    from erk_shared.gateway.console.fake import FakeConsole
    from erk_shared.gateway.git.fake import FakeGit
    from erk_shared.gateway.github.fake import FakeGitHub
    from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
    from erk_shared.gateway.graphite.fake import FakeGraphite

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_plan_store, fake_backing = create_plan_store(plans, backend=backend)

    git_kwargs = git_kwargs or {}
    if "current_branches" not in git_kwargs:
        git_kwargs["current_branches"] = {repo_root: "main"}
    if "trunk_branches" not in git_kwargs:
        git_kwargs["trunk_branches"] = {repo_root: "master"}

    # Auto-add remote branch refs for planned_pr branches
    if backend == "planned_pr" and remote_branch_refs is None and "remote_branches" not in git_kwargs:
        refs = ["origin/main"]
        # Add remote refs for each plan's branch
        for plan_id, plan in plans.items():
            branch_name = f"plnd/{plan_id}-{plan.title.lower().replace(' ', '-')}"
            refs.append(f"origin/{branch_name}")
        git_kwargs["remote_branches"] = {repo_root: refs}
    elif remote_branch_refs is not None:
        git_kwargs["remote_branches"] = {repo_root: remote_branch_refs}

    fake_git = FakeGit(**git_kwargs)

    # For planned_pr backend, set up PRDetails in FakeGitHub
    github_kwargs = github_kwargs or {}
    if backend == "planned_pr" and "pr_details" not in github_kwargs:
        # Auto-generate PRDetails for each plan
        pr_details_dict = pr_details_map or {}
        if not pr_details_dict:
            for plan_id, plan in plans.items():
                # Generate plnd/ prefixed branch name
                branch_name = f"plnd/{plan_id}-{plan.title.lower().replace(' ', '-')}"
                pr_details_dict[int(plan_id)] = create_pr_details_for_plan(
                    plan, branch_name, "main"
                )
        github_kwargs["pr_details"] = pr_details_dict

    fake_github = FakeGitHub(**github_kwargs)
    # When use_graphite=False, use GraphiteDisabled sentinel to match production behavior
    if use_graphite:
        fake_graphite = FakeGraphite(**(graphite_kwargs or {}))
    else:
        from erk_shared.gateway.graphite.disabled import (
            GraphiteDisabled,
            GraphiteDisabledReason,
        )

        fake_graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

    # Update issues kwargs if provided (only applicable to github backend)
    if issues_kwargs and isinstance(fake_backing, FakeGitHubIssues):
        for key, value in issues_kwargs.items():
            setattr(fake_backing, f"_{key}", value)

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

    # Wire up issues gateway: use explicit issues if provided, otherwise
    # for github backend use the fake backing, for planned_pr let context_for_test create default
    if issues is not None:
        fake_issues = issues
    elif isinstance(fake_backing, FakeGitHubIssues):
        fake_issues = fake_backing
    else:
        fake_issues = None

    # Configure FakePromptExecutor to simulate failure so that
    # generate_slug_or_fallback falls back to the raw title.
    # This keeps branch name assertions stable in tests.
    fake_prompt_executor = FakePromptExecutor(
        available=True,
        simulated_prompt_error="LLM unavailable in test",
    )

    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        plan_store=fake_plan_store,
        graphite=fake_graphite,
        repo=repo,
        global_config=global_config,
        console=fake_console,
        prompt_executor=fake_prompt_executor,
    )

    return ctx, fake_git, fake_github, fake_backing, fake_graphite, repo_root

"""Doctor workflow subcommand for workflow-specific diagnostics.

Runs GitHub-focused health checks and optionally dispatches a live
smoke test to verify the full CI pipeline works end-to-end.
"""

import click

from erk.artifacts.artifact_health import get_artifact_health, is_erk_managed
from erk.artifacts.discovery import discover_artifacts
from erk.artifacts.models import ArtifactFileState
from erk.artifacts.paths import ErkPackageInfo
from erk.artifacts.state import load_artifact_state, load_installed_capabilities
from erk.cli.commands.doctor import _format_check_result
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.commands.run import run_group
from erk.core.context import ErkContext, NoRepoSentinel
from erk.core.health_checks import (
    CheckResult,
    check_anthropic_api_secret,
    check_erk_queue_pat_secret,
    check_github_auth,
    check_workflow_permissions,
)
from erk.core.workflow_smoke_test import SmokeTestError, cleanup_smoke_tests, run_smoke_test
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation


def _get_repo_location(ctx: ErkContext) -> tuple[str, str] | None:
    """Get (owner, repo) from ErkContext, or None if not a GitHub repo."""
    if isinstance(ctx.repo, NoRepoSentinel):
        return None
    if ctx.repo.github is None:
        return None
    return (ctx.repo.github.owner, ctx.repo.github.repo)


def _check_claude_enabled_variable(ctx: ErkContext) -> CheckResult:
    """Check if CLAUDE_ENABLED repo variable is set."""
    owner_repo = _get_repo_location(ctx)
    if owner_repo is None:
        return CheckResult(
            name="claude-enabled-variable",
            passed=True,
            message="Not a GitHub repository",
            info=True,
        )

    repo_id = GitHubRepoId(owner=owner_repo[0], repo=owner_repo[1])
    location = GitHubRepoLocation(root=ctx.repo_root, repo_id=repo_id)

    value = ctx.github_admin.get_variable(location, "CLAUDE_ENABLED")
    if value is not None:
        return CheckResult(
            name="claude-enabled-variable",
            passed=True,
            message=f"CLAUDE_ENABLED variable set ({value})",
        )
    return CheckResult(
        name="claude-enabled-variable",
        passed=True,
        message="CLAUDE_ENABLED variable not set",
        info=True,
        details="Set via: gh variable set CLAUDE_ENABLED -b true",
    )


def _check_workflow_artifacts_installed(ctx: ErkContext) -> CheckResult:
    """Check if workflow + action artifacts are installed."""
    if isinstance(ctx.repo, NoRepoSentinel):
        return CheckResult(
            name="workflow-artifacts",
            passed=True,
            message="Not in a git repository",
            info=True,
        )

    repo_root = ctx.repo.root
    package = ErkPackageInfo.from_project_dir(repo_root)
    installed_capabilities: frozenset[str] | None = None
    if not package.in_erk_repo:
        installed_capabilities = load_installed_capabilities(repo_root)

    state = load_artifact_state(repo_root)
    saved_files: dict[str, ArtifactFileState] = dict(state.files) if state else {}

    result = get_artifact_health(
        repo_root,
        saved_files,
        installed_capabilities=installed_capabilities,
        package=package,
    )

    if result.skipped_reason is not None:
        return CheckResult(
            name="workflow-artifacts",
            passed=True,
            message="Artifact check skipped",
            info=True,
        )

    # Check workflow and action artifacts specifically
    workflow_artifacts = [a for a in result.artifacts if a.name.startswith("workflows/")]
    action_artifacts = [a for a in result.artifacts if a.name.startswith("actions/")]

    missing_workflows = [a for a in workflow_artifacts if a.status == "not-installed"]
    missing_actions = [a for a in action_artifacts if a.status == "not-installed"]

    if missing_workflows:
        names = ", ".join(a.name for a in missing_workflows)
        return CheckResult(
            name="workflow-artifacts",
            passed=False,
            message=f"Missing workflow artifacts: {names}",
            remediation="Run 'erk artifact sync' to install workflows",
        )

    if missing_actions and workflow_artifacts:
        names = ", ".join(a.name for a in missing_actions)
        return CheckResult(
            name="workflow-artifacts",
            passed=False,
            message=f"Missing action artifacts: {names}",
            remediation="Run 'erk artifact sync' to install actions",
        )

    installed_count = len(workflow_artifacts) + len(action_artifacts)
    if installed_count == 0:
        return CheckResult(
            name="workflow-artifacts",
            passed=True,
            message="No workflow artifacts configured",
            info=True,
        )

    return CheckResult(
        name="workflow-artifacts",
        passed=True,
        message=(
            f"Workflow artifacts installed"
            f" ({len(workflow_artifacts)} workflows, {len(action_artifacts)} actions)"
        ),
    )


def _run_static_checks(ctx: ErkContext, *, verbose: bool) -> list[CheckResult]:
    """Run workflow-focused static checks and return results."""
    repo_root = ctx.repo_root
    admin = ctx.github_admin

    results = [
        check_github_auth(ctx.shell, admin),
        check_workflow_permissions(ctx, repo_root, admin),
        check_erk_queue_pat_secret(ctx, repo_root, admin),
        check_anthropic_api_secret(ctx, repo_root, admin),
        _check_claude_enabled_variable(ctx),
        _check_workflow_artifacts_installed(ctx),
    ]
    return results


@click.group("workflow", invoke_without_command=True)
@click.pass_context
def workflow_group(ctx: click.Context) -> None:
    """Workflow diagnostics and management.

    \b
    Examples:

    \b
      # List installed workflow files
      erk workflow list

      # Check workflow prerequisites
      erk workflow check

      # Run a live smoke test
      erk workflow smoke-test

      # Run smoke test and wait for completion
      erk workflow smoke-test --wait

      # Clean up old smoke test artifacts
      erk workflow cleanup
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _display_static_checks(results: list[CheckResult], *, verbose: bool) -> tuple[bool, bool]:
    """Display static check results and return (all_passed, critical_failed)."""
    click.echo(click.style("Workflow Checks", bold=True))

    all_passed = True
    critical_failed = False
    for result in results:
        _format_check_result(result, verbose=verbose)
        if not result.passed:
            all_passed = False
            if result.name == "github-auth":
                critical_failed = True

    click.echo("")

    if all_passed:
        click.echo(click.style("Ready to dispatch workflows", fg="green", bold=True))
    else:
        click.echo(click.style("Some checks have issues (see above)", fg="yellow", bold=True))

    return all_passed, critical_failed


@workflow_group.command("check")
@click.option("-v", "--verbose", is_flag=True, help="Show details of static checks")
@click.pass_obj
def workflow_check_cmd(ctx: ErkContext, verbose: bool) -> None:
    """Check workflow setup prerequisites."""
    results = _run_static_checks(ctx, verbose=verbose)
    _display_static_checks(results, verbose=verbose)


@workflow_group.command("smoke-test")
@click.option("--wait", is_flag=True, help="Poll workflow run until completion")
@click.option("-v", "--verbose", is_flag=True, help="Show details of static checks")
@click.option(
    "--ref",
    "dispatch_ref",
    type=str,
    default=None,
    help="Branch to dispatch workflow from (overrides config dispatch_ref)",
)
@click.option(
    "--ref-current",
    is_flag=True,
    default=False,
    help="Dispatch workflow from the current branch",
)
@click.pass_obj
def workflow_smoke_test_cmd(
    ctx: ErkContext, wait: bool, verbose: bool, dispatch_ref: str | None, ref_current: bool
) -> None:
    """Run a live smoke test (creates artifacts).

    Runs static checks first, then dispatches a throwaway branch/PR
    to verify the full CI pipeline end-to-end.
    """
    results = _run_static_checks(ctx, verbose=verbose)
    _all_passed, critical_failed = _display_static_checks(results, verbose=verbose)

    if critical_failed:
        click.echo("")
        click.echo(
            click.style("Error: Cannot run smoke test — critical checks failed", fg="red"),
            err=True,
        )
        raise SystemExit(1)

    click.echo("")
    _handle_smoke_test(ctx, wait=wait, dispatch_ref=dispatch_ref, ref_current=ref_current)


@workflow_group.command("cleanup")
@click.pass_obj
def workflow_cleanup_cmd(ctx: ErkContext) -> None:
    """Clean up old smoke test branches and PRs."""
    _handle_cleanup(ctx)


workflow_group.add_command(run_group)


@workflow_group.command("list")
@click.pass_obj
def workflow_list_cmd(ctx: ErkContext) -> None:
    """List installed workflow files."""
    project_dir = ctx.repo_root
    workflows_dir = project_dir / ".github" / "workflows"

    if not workflows_dir.exists():
        click.echo("No .github/workflows/ directory found")
        return

    artifacts = discover_artifacts(project_dir)
    workflow_artifacts = [a for a in artifacts if a.artifact_type == "workflow"]

    if not workflow_artifacts:
        click.echo("No workflow files found")
        return

    for artifact in workflow_artifacts:
        managed = is_erk_managed(artifact)
        if managed:
            badge = click.style(" [erk]", fg="cyan")
        else:
            badge = click.style(" [unmanaged]", fg="yellow")
        click.echo(f"  {artifact.name}{badge}")


def _handle_smoke_test(
    ctx: ErkContext,
    *,
    wait: bool,
    dispatch_ref: str | None,
    ref_current: bool,
) -> None:
    """Run the live smoke test dispatch."""
    click.echo(click.style("Running smoke test...", bold=True))

    ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
    result = run_smoke_test(ctx, dispatch_ref=ref)

    if isinstance(result, SmokeTestError):
        click.echo(click.style(f"Error during {result.step}: {result.message}", fg="red"), err=True)
        raise SystemExit(1)

    click.echo(click.style("Smoke test dispatched!", fg="green", bold=True))
    click.echo(f"  Branch: {result.branch_name}")
    click.echo(f"  PR: #{result.pr_number}")
    click.echo(f"  Run ID: {result.run_id}")
    if result.run_url is not None:
        click.echo(f"  Run URL: {click.style(result.run_url, fg='cyan')}")

    if wait:
        click.echo("")
        _poll_workflow_run(ctx, result.run_id, result.run_url)


def _report_workflow_result(conclusion: str | None, run_url: str | None) -> None:
    """Report the result of a completed workflow run, exiting on failure."""
    if conclusion == "success":
        click.echo(click.style("Workflow completed successfully!", fg="green"))
        return
    click.echo(click.style(f"Workflow completed with conclusion: {conclusion}", fg="red"))
    if run_url is not None:
        click.echo(f"  Check logs: {run_url}")
    raise SystemExit(1)


def _poll_workflow_run(ctx: ErkContext, run_id: str, run_url: str | None) -> None:
    """Poll a workflow run until completion or timeout."""
    if isinstance(ctx.repo, NoRepoSentinel):
        return

    timeout_seconds = 600  # 10 minutes
    poll_interval = 15  # seconds
    elapsed = 0

    click.echo(f"Waiting for workflow run {run_id} to complete (timeout: {timeout_seconds}s)...")

    while elapsed < timeout_seconds:
        runs = ctx.github.list_workflow_runs(ctx.repo.root, "one-shot.yml", limit=10)
        matching = [r for r in runs if r.run_id == run_id]
        if matching and matching[0].status == "completed":
            _report_workflow_result(matching[0].conclusion, run_url)
            return

        ctx.time.sleep(poll_interval)
        elapsed += poll_interval
        click.echo(click.style(f"  Still running... ({elapsed}s elapsed)", dim=True))

    click.echo(
        click.style(f"Timeout: workflow did not complete within {timeout_seconds}s", fg="yellow")
    )
    if run_url is not None:
        click.echo(f"  Check status: {run_url}")


def _handle_cleanup(ctx: ErkContext) -> None:
    """Clean up old smoke test branches and PRs."""
    click.echo(click.style("Cleaning up smoke test artifacts...", bold=True))

    items = cleanup_smoke_tests(ctx)

    if not items:
        click.echo("No smoke test artifacts found.")
        return

    for item in items:
        parts = [f"  {item.branch_name}"]
        if item.closed_pr and item.pr_number is not None:
            parts.append(f"closed PR #{item.pr_number}")
        if item.deleted_branch:
            parts.append("deleted remote branch")
        click.echo(" — ".join(parts))

    click.echo(f"\nCleaned up {len(items)} smoke test artifact(s).")

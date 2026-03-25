"""Human command for objective check with [PASS]/[FAIL] output."""

import json

import click

from erk.cli.commands.objective.check.operation import (
    ObjectiveCheckRequest,
    ObjectiveCheckResult,
    run_objective_check,
)
from erk.cli.repo_resolution import resolved_repo_option
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.cli_alias import alias
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.output.output import user_output


@alias("ch")
@click.command("check")
@click.argument("objective_ref", type=str)
@click.option(
    "--json-output",
    "json_mode",
    is_flag=True,
    help="[Deprecated: use 'erk json objective check'] Output structured JSON",
)
@resolved_repo_option
@click.pass_obj
def check_objective(
    ctx: ErkContext,
    objective_ref: str,
    *,
    json_mode: bool,
    repo_id: GitHubRepoId,
) -> None:
    """Validate an objective's format and roadmap consistency.

    OBJECTIVE_REF can be an issue number (42) or a full GitHub URL.

    Checks: erk-objective label, roadmap parsing, status/PR consistency,
    orphaned statuses, phase numbering, v2 format integrity, PR reference
    format, and roadmap table sync.

    Use --json-output for structured JSON output (replaces erk exec objective-roadmap-check).
    """
    request = ObjectiveCheckRequest(identifier=objective_ref)
    result = run_objective_check(ctx, request, repo_id=repo_id)

    if isinstance(result, MachineCommandError):
        if json_mode:
            click.echo(json.dumps({"success": False, "error": result.message}))
            raise SystemExit(1)
        user_output(
            click.style("Error: ", fg="red") + f"Failed to validate objective: {result.message}"
        )
        raise SystemExit(1)

    if json_mode:
        click.echo(json.dumps(result.to_json_dict()))
        if not result.validation.passed:
            raise SystemExit(1)
        return

    _render_human(result)


def _render_human(result: ObjectiveCheckResult) -> None:
    """Render [PASS]/[FAIL] output."""
    v = result.validation

    user_output(f"Validating objective #{result.issue_number}...")
    user_output("")

    for passed, description in v.checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    if v.passed:
        summary = v.summary
        if summary:
            user_output(
                click.style("Objective validation passed", fg="green")
                + f" ({summary.get('done', 0)}/{summary.get('total_nodes', 0)} done)"
            )
        else:
            user_output(click.style("Objective validation passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "checks" if v.failed_count > 1 else "check"
        user_output(
            click.style(
                f"Objective validation failed ({v.failed_count} {check_word} failed)", fg="red"
            )
        )
        raise SystemExit(1)

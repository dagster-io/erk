"""Create git commit and submit current branch with Graphite (two-phase) CLI command."""

import json
from pathlib import Path

import click
from dot_agent_kit.cli.schema_formatting import json_output
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.operations.preflight import execute_preflight
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import (
    FinalizeResult,
    PostAnalysisError,
    PreAnalysisError,
    PreflightResult,
)


@click.group()
def pr_submit() -> None:
    """Create git commit and submit current branch with Graphite (two-phase)."""
    pass


@json_output(PreflightResult | PreAnalysisError | PostAnalysisError)
@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID for scratch file isolation. "
    "Writes diff to .tmp/<session-id>/ in repo root.",
)
def preflight(session_id: str) -> None:
    """Execute preflight phase: auth, squash, submit, get diff.

    Returns JSON with PR info and path to temp diff file for AI analysis.
    This is phase 1 of the 3-phase workflow for slash command orchestration.
    """
    try:
        ops = RealGtKit()
        cwd = Path.cwd()
        result = render_events(execute_preflight(ops, cwd, session_id))
        click.echo(json.dumps(result, indent=2))

        if not result["success"]:
            raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


@json_output(FinalizeResult | PostAnalysisError)
@click.command()
@click.option("--pr-number", required=True, type=int, help="PR number to update")
@click.option("--pr-title", required=True, help="AI-generated PR title")
@click.option("--pr-body", required=False, help="AI-generated PR body (text)")
@click.option(
    "--pr-body-file",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    help="Path to file containing PR body (mutually exclusive with --pr-body)",
)
@click.option("--diff-file", required=False, help="Temp diff file to clean up")
def finalize(
    pr_number: int,
    pr_title: str,
    pr_body: str | None,
    pr_body_file: Path | None,
    diff_file: str | None,
) -> None:
    """Execute finalize phase: update PR metadata.

    This is phase 3 of the 3-phase workflow for slash command orchestration.
    Accepts PR body either as inline text (--pr-body) or from a file (--pr-body-file).
    """
    try:
        ops = RealGtKit()
        cwd = Path.cwd()
        result = render_events(
            execute_finalize(ops, cwd, pr_number, pr_title, pr_body, pr_body_file, diff_file)
        )
        click.echo(json.dumps(result, indent=2))

        if not result["success"]:
            raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Validation error: {e}", err=True)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


# Register subcommands
pr_submit.add_command(preflight)
pr_submit.add_command(finalize)

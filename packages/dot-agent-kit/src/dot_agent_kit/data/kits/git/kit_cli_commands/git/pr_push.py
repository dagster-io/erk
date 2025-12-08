"""Git-only PR push workflow CLI commands (two-phase).

This provides the preflight and finalize commands for git-only PR
workflows (no Graphite required).

Usage:
    # Phase 1: Preflight - stage, push, create PR, get diff
    dot-agent kit-command git pr-push preflight --session-id <id>

    # Phase 2: Finalize - update PR metadata
    dot-agent kit-command git pr-push finalize --pr-number 123 --pr-title "..." --pr-body "..."
"""

import json
from dataclasses import asdict
from pathlib import Path

import click
from erk_shared.integrations.git_pr.operations.finalize import execute_finalize
from erk_shared.integrations.git_pr.operations.preflight import execute_preflight
from erk_shared.integrations.git_pr.types import (
    GitFinalizeError,
    GitPreflightError,
)
from erk_shared.integrations.gt.cli import render_events

from dot_agent_kit.context_helpers import require_cwd


@click.group()
def pr_push() -> None:
    """Git-only PR push workflow commands (two-phase)."""
    pass


@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID for scratch file isolation. "
    "Writes diff to .tmp/<session-id>/ in repo root.",
)
@click.pass_context
def preflight(ctx: click.Context, session_id: str) -> None:
    """Execute preflight phase: auth, stage, push, create PR, get diff.

    Returns JSON with PR info and path to temp diff file for AI analysis.
    This is phase 1 of the 2-phase workflow for git-only PR submission.
    """
    try:
        cwd = require_cwd(ctx)
        ops = ctx.obj  # DotAgentContext satisfies GitPrKit Protocol

        result = render_events(execute_preflight(ops, cwd, session_id))
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, GitPreflightError):
            raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


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
@click.pass_context
def finalize(
    ctx: click.Context,
    pr_number: int,
    pr_title: str,
    pr_body: str | None,
    pr_body_file: Path | None,
    diff_file: str | None,
) -> None:
    """Execute finalize phase: update PR metadata.

    This is phase 2 of the 2-phase workflow for git-only PR submission.
    Accepts PR body either as inline text (--pr-body) or from a file (--pr-body-file).
    """
    try:
        cwd = require_cwd(ctx)
        ops = ctx.obj  # DotAgentContext satisfies GitPrKit Protocol

        result = render_events(
            execute_finalize(ops, cwd, pr_number, pr_title, pr_body, pr_body_file, diff_file)
        )
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, GitFinalizeError):
            raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Validation error: {e}", err=True)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


# Register subcommands
pr_push.add_command(preflight)
pr_push.add_command(finalize)

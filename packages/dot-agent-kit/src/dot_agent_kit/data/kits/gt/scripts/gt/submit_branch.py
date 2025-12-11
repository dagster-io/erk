"""Create git commit and submit current branch with Graphite (two-phase) CLI command.

Updated to use the two-layer architecture:
1. Core layer: git push + gh pr create (via execute_core_submit)
2. Graphite layer: Optional gt submit for stack metadata (via execute_graphite_enhance)
"""

import json
from dataclasses import asdict
from pathlib import Path

import click
from erk_shared.context.factories import create_minimal_context
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.types import PostAnalysisError
from erk_shared.integrations.pr.diff_extraction import execute_diff_extraction
from erk_shared.integrations.pr.graphite_enhance import execute_graphite_enhance
from erk_shared.integrations.pr.submit import execute_core_submit
from erk_shared.integrations.pr.types import (
    CoreSubmitError,
    GraphiteEnhanceError,
    GraphiteEnhanceResult,
)


@click.group()
def pr_submit() -> None:
    """Create git commit and submit current branch with Graphite (two-phase)."""
    pass


@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID for scratch file isolation. "
    "Writes diff to .tmp/<session-id>/ in repo root.",
)
@click.option(
    "--no-graphite",
    is_flag=True,
    help="Skip Graphite enhancement (use git + gh only)",
)
def preflight(session_id: str, no_graphite: bool) -> None:
    """Execute preflight phase: core submit + diff extraction.

    Uses two-layer architecture:
    1. Core submit: git push + gh pr create
    2. Diff extraction: Get PR diff for AI analysis
    3. Graphite enhancement (optional): gt submit for stack metadata

    Returns JSON with PR info and path to temp diff file for AI analysis.
    This is phase 1 of the 2-phase workflow for slash command orchestration.
    """
    _execute_preflight(session_id, use_graphite=not no_graphite)


def _execute_preflight(session_id: str, use_graphite: bool) -> None:
    """Execute preflight phase with positively-named parameters."""
    try:
        ctx = create_minimal_context(debug=False)
        cwd = Path.cwd()

        # Phase 1: Core submit (git push + gh pr create)
        click.echo("Phase 1: Core submit (git push + gh pr create)...", err=True)
        core_result = render_events(execute_core_submit(ctx, cwd, pr_title="WIP", pr_body=""))

        if isinstance(core_result, CoreSubmitError):
            click.echo(json.dumps(asdict(core_result), indent=2))
            raise SystemExit(1)

        click.echo(f"Created PR #{core_result.pr_number}", err=True)

        # Phase 2: Get diff for AI
        click.echo("Phase 2: Getting diff for AI...", err=True)
        diff_result = render_events(
            execute_diff_extraction(ctx, cwd, core_result.pr_number, session_id)
        )

        if diff_result is None:
            error_result = {
                "success": False,
                "error_type": "diff_extraction_failed",
                "message": "Failed to extract diff for AI analysis",
                "details": {},
            }
            click.echo(json.dumps(error_result, indent=2))
            raise SystemExit(1)

        # Phase 3: Graphite enhancement (optional)
        graphite_url: str | None = None
        if use_graphite:
            click.echo("Phase 3: Graphite enhancement...", err=True)
            graphite_result = render_events(
                execute_graphite_enhance(ctx, cwd, core_result.pr_number)
            )
            if isinstance(graphite_result, GraphiteEnhanceError):
                # Graphite errors are warnings, not fatal
                click.echo(f"Warning: {graphite_result.message}", err=True)
            elif isinstance(graphite_result, GraphiteEnhanceResult):
                graphite_url = graphite_result.graphite_url

        # Build result that matches PreflightResult structure for backwards compatibility
        repo_root = ctx.git.get_repository_root(cwd)
        current_branch = ctx.git.get_current_branch(cwd) or core_result.branch_name
        trunk_branch = ctx.git.detect_trunk_branch(repo_root)
        commit_messages = ctx.git.get_commit_messages_since(cwd, trunk_branch)

        result = {
            "success": True,
            "pr_number": core_result.pr_number,
            "pr_url": core_result.pr_url,
            "graphite_url": graphite_url or "",
            "branch_name": core_result.branch_name,
            "diff_file": str(diff_result),
            "repo_root": str(repo_root),
            "current_branch": current_branch,
            "parent_branch": trunk_branch,
            "issue_number": core_result.issue_number,
            "message": (
                f"Preflight complete for branch: {core_result.branch_name}\n"
                f"PR #{core_result.pr_number}: {core_result.pr_url}"
            ),
            "commit_messages": commit_messages,
        }

        click.echo(json.dumps(result, indent=2))

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
def finalize(
    pr_number: int,
    pr_title: str,
    pr_body: str | None,
    pr_body_file: Path | None,
    diff_file: str | None,
) -> None:
    """Execute finalize phase: update PR metadata.

    This is phase 2 of the 2-phase workflow for slash command orchestration.
    Accepts PR body either as inline text (--pr-body) or from a file (--pr-body-file).
    """
    try:
        ctx = create_minimal_context(debug=False)
        cwd = Path.cwd()
        result = render_events(
            execute_finalize(ctx, cwd, pr_number, pr_title, pr_body, pr_body_file, diff_file)
        )
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, PostAnalysisError):
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
pr_submit.add_command(preflight)
pr_submit.add_command(finalize)

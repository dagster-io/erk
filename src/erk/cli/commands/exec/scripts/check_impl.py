"""Check .impl/ folder structure and validate prerequisites.

This exec command validates that .impl/ folder has required files
(plan.md, progress.md) and checks for optional GitHub issue tracking.

Usage:
    erk exec check-impl
    erk exec check-impl --dry-run

Output:
    JSON with validation status and tracking info (dry-run mode)
    Instructions for implementation (normal mode)

Exit Codes:
    0: Success
    1: Validation error

Examples:
    $ erk exec check-impl --dry-run
    {"valid": true, "has_plan_tracking": true, "plan_length": 1234}

    $ erk exec check-impl
    Plan loaded from .impl/plan.md
    GitHub tracking: ENABLED (issue #123)
    ...
"""

import json
from pathlib import Path
from typing import NoReturn

import click

from erk_shared.context.helpers import require_cwd, require_git
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir


def _error(msg: str) -> NoReturn:
    """Output error message and exit with code 1."""
    click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


def _validate_impl_folder(ctx: click.Context) -> Path:
    """Validate implementation folder exists and has required files.

    Uses resolve_impl_dir() for branch-scoped discovery.

    Args:
        ctx: Click context for dependency injection.

    Returns:
        Path to implementation directory

    Raises:
        SystemExit: If validation fails
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    branch_name = git.branch.get_current_branch(cwd)

    impl_dir = resolve_impl_dir(cwd, branch_name=branch_name)

    if impl_dir is None:
        click.echo("Error: No implementation folder found in current directory", err=True)
        raise SystemExit(1)

    plan_file = impl_dir / "plan.md"
    if not plan_file.exists():
        _error(f"No plan.md found in {impl_dir.name}/ folder")

    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        _error(f"No progress.md found in {impl_dir.name}/ folder")

    return impl_dir


def _get_plan_reference(impl_dir: Path, *, silent: bool = False) -> dict[str, int | str] | None:
    """Get plan reference if available, None if not (non-fatal).

    Args:
        impl_dir: Path to .impl/ directory
        silent: If True, don't print info message when tracking disabled

    Returns:
        Dict with plan_number and plan_url, or None if not available
    """
    plan_ref = read_plan_ref(impl_dir)

    if plan_ref is None:
        # Not an error - just means no GitHub tracking
        if not silent:
            click.echo(
                "ℹ️  No issue reference found - GitHub progress tracking disabled",
                err=True,
            )
        return None

    return {
        "plan_number": int(plan_ref.plan_id),
        "plan_url": plan_ref.url,
    }


def _execute_plan(plan_content: str, plan_info: dict[str, int | str] | None) -> None:
    """Display plan execution instructions.

    Args:
        plan_content: Content of plan.md
        plan_info: Plan info dict or None
    """
    if plan_info:
        tracking_msg = f"GitHub tracking: ENABLED (issue #{plan_info['plan_number']})"
    else:
        tracking_msg = "GitHub tracking: DISABLED (no issue.json)"

    msg = f"""
Plan loaded from .impl/plan.md

{tracking_msg}

To implement:
  claude --permission-mode acceptEdits "/erk:plan-implement"

The /erk:plan-implement slash command will:
  1. Execute implementation steps
  2. Update progress.md as steps complete"""

    if plan_info:
        msg += f"\n  3. Post progress to GitHub issue #{plan_info['plan_number']}"

    click.echo(msg)


@click.command(name="check-impl")
@click.option("--dry-run", is_flag=True, help="Validate and output JSON")
@click.pass_context
def check_impl(ctx: click.Context, dry_run: bool) -> None:
    """Check implementation folder structure and validate prerequisites.

    Validates that implementation folder exists with required files (plan.md, progress.md).
    Checks for optional plan-ref.json to enable GitHub progress tracking.

    In dry-run mode, outputs JSON with validation status.
    In normal mode, outputs instructions for running the implementation.
    """
    impl_dir = _validate_impl_folder(ctx)
    # In dry-run mode, suppress info messages to keep JSON output clean
    plan_info = _get_plan_reference(impl_dir, silent=dry_run)

    plan_file = impl_dir / "plan.md"
    plan_content = plan_file.read_text(encoding="utf-8")

    if dry_run:
        result = {
            "valid": True,
            "has_plan_tracking": plan_info is not None,
            "plan_length": len(plan_content),
        }
        click.echo(json.dumps(result))
        return

    _execute_plan(plan_content, plan_info)

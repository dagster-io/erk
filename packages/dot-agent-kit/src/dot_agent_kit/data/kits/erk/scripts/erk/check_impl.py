"""Check .impl/ folder structure and validate prerequisites.

This kit CLI command validates that .impl/ folder has required files
(plan.md, progress.md) and checks for optional GitHub issue tracking.

Usage:
    dot-agent run erk check-impl
    dot-agent run erk check-impl --dry-run

Output:
    JSON with validation status and tracking info (dry-run mode)
    Instructions for implementation (normal mode)

Exit Codes:
    0: Success
    1: Validation error

Examples:
    $ dot-agent run erk check-impl --dry-run
    {"valid": true, "has_issue_tracking": true, "plan_length": 1234}

    $ dot-agent run erk check-impl
    Plan loaded from .impl/plan.md
    GitHub tracking: ENABLED (issue #123)
    ...
"""

import json
from pathlib import Path
from typing import NoReturn

import click
from erk_shared.impl_folder import read_issue_reference


def _error(msg: str) -> NoReturn:
    """Output error message and exit with code 1."""
    click.echo(f"❌ Error: {msg}", err=True)
    raise SystemExit(1)


def _validate_impl_folder() -> Path:
    """Validate .impl/ folder exists and has required files.

    Returns:
        Path to .impl/ directory

    Raises:
        SystemExit: If validation fails
    """
    impl_dir = Path.cwd() / ".impl"

    if not impl_dir.exists():
        _error("No .impl/ folder found in current directory")

    plan_file = impl_dir / "plan.md"
    if not plan_file.exists():
        _error("No plan.md found in .impl/ folder")

    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        _error("No progress.md found in .impl/ folder")

    return impl_dir


def _get_issue_reference(impl_dir: Path, *, silent: bool = False) -> dict[str, int | str] | None:
    """Get issue reference if available, None if not (non-fatal).

    Args:
        impl_dir: Path to .impl/ directory
        silent: If True, don't print info message when tracking disabled

    Returns:
        Dict with issue_number and issue_url, or None if not available
    """
    issue_ref = read_issue_reference(impl_dir)

    if issue_ref is None:
        # Not an error - just means no GitHub tracking
        if not silent:
            click.echo(
                "ℹ️  No issue reference found - GitHub progress tracking disabled",
                err=True,
            )
        return None

    return {
        "issue_number": issue_ref.issue_number,
        "issue_url": issue_ref.issue_url,
    }


def _execute_plan(plan_content: str, issue_info: dict[str, int | str] | None) -> None:
    """Display plan execution instructions.

    Args:
        plan_content: Content of plan.md
        issue_info: Issue info dict or None
    """
    if issue_info:
        tracking_msg = f"GitHub tracking: ENABLED (issue #{issue_info['issue_number']})"
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

    if issue_info:
        msg += f"\n  3. Post progress to GitHub issue #{issue_info['issue_number']}"

    click.echo(msg)


@click.command(name="check-impl")
@click.option("--dry-run", is_flag=True, help="Validate and output JSON")
def check_impl(dry_run: bool) -> None:
    """Check .impl/ folder structure and validate prerequisites.

    Validates that .impl/ folder exists with required files (plan.md, progress.md).
    Checks for optional issue.json to enable GitHub progress tracking.

    In dry-run mode, outputs JSON with validation status.
    In normal mode, outputs instructions for running the implementation.
    """
    impl_dir = _validate_impl_folder()
    # In dry-run mode, suppress info messages to keep JSON output clean
    issue_info = _get_issue_reference(impl_dir, silent=dry_run)

    plan_file = impl_dir / "plan.md"
    plan_content = plan_file.read_text(encoding="utf-8")

    if dry_run:
        result = {
            "valid": True,
            "has_issue_tracking": issue_info is not None,
            "plan_length": len(plan_content),
        }
        click.echo(json.dumps(result))
        return

    _execute_plan(plan_content, issue_info)

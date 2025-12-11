"""Quick commit all changes and submit with Graphite CLI command."""

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import click


@dataclass(frozen=True)
class QuickSubmitSuccess:
    """Result when quick-submit succeeds."""

    success: bool
    staged_changes: bool
    committed: bool
    message: str


@dataclass(frozen=True)
class QuickSubmitError:
    """Result when quick-submit fails."""

    success: bool
    error: str
    stage: str  # "stage", "commit", or "submit"


def _run_git_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _has_staged_changes(cwd: Path) -> bool:
    """Check if there are staged changes."""
    result = _run_git_command(["diff", "--cached", "--quiet"], cwd)
    # Exit code 0 = no changes, 1 = has changes
    return result.returncode != 0


@click.command("quick-submit")
def quick_submit() -> None:
    """Quick commit all changes and submit with Graphite.

    Stages all changes, commits with "update" message if there are changes,
    then runs gt submit. This is a fast iteration shortcut.

    For proper commit messages, use the pr-submit command instead.
    """
    cwd = Path.cwd()

    # Stage all changes
    stage_result = _run_git_command(["add", "-A"], cwd)
    if stage_result.returncode != 0:
        result = QuickSubmitError(
            success=False,
            error=stage_result.stderr.strip() or "Failed to stage changes",
            stage="stage",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1)

    # Check if there are staged changes
    has_changes = _has_staged_changes(cwd)
    committed = False

    # Commit if there are staged changes
    if has_changes:
        commit_result = _run_git_command(["commit", "-m", "update"], cwd)
        if commit_result.returncode != 0:
            result = QuickSubmitError(
                success=False,
                error=commit_result.stderr.strip() or "Failed to commit changes",
                stage="commit",
            )
            click.echo(json.dumps(asdict(result), indent=2))
            raise SystemExit(1)
        committed = True

    # Run gt submit
    submit_result = subprocess.run(
        ["gt", "submit", "--no-edit", "--no-interactive"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    if submit_result.returncode != 0:
        error_msg = (
            submit_result.stderr.strip() or submit_result.stdout.strip() or "Failed to submit"
        )
        result = QuickSubmitError(
            success=False,
            error=error_msg,
            stage="submit",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1)

    # Success
    msg = (
        "Changes submitted successfully"
        if committed
        else "No new changes, submitted existing commits"
    )
    result_obj = QuickSubmitSuccess(
        success=True,
        staged_changes=has_changes,
        committed=committed,
        message=msg,
    )
    click.echo(json.dumps(asdict(result_obj), indent=2))

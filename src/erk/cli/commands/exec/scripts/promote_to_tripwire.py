"""Promote a tripwire candidate to documentation frontmatter.

Usage:
    erk exec promote-to-tripwire --target-doc <path> --action <text> --warning <text> [--no-sync]

Adds a tripwire entry to the target doc's YAML frontmatter. By default,
runs `erk docs sync` afterward to regenerate tripwires.md.

Exit Codes:
    0: Success (tripwire added or already exists)
    1: Error (file not found, parse error)
"""

import json
import subprocess
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_repo_root
from erk_shared.learn.tripwire_promotion import promote_tripwire_to_frontmatter


@dataclass(frozen=True)
class PromoteSuccess:
    """Success response for tripwire promotion."""

    success: bool
    target_doc_path: str


@dataclass(frozen=True)
class PromoteError:
    """Error response for tripwire promotion."""

    success: bool
    error: str
    target_doc_path: str


@click.command(name="promote-to-tripwire")
@click.option("--target-doc", required=True, help="Relative path within docs/learned/")
@click.option("--action", required=True, help="Action pattern to detect")
@click.option("--warning", required=True, help="Warning message to display")
@click.option(
    "--sync/--no-sync",
    "sync_flag",
    default=True,
    help="Run erk docs sync afterward (default: sync)",
)
@click.pass_context
def promote_to_tripwire(
    ctx: click.Context,
    *,
    target_doc: str,
    action: str,
    warning: str,
    sync_flag: bool,
) -> None:
    """Add a tripwire to a documentation file's frontmatter.

    Writes the tripwire entry into the target doc's YAML frontmatter,
    then optionally runs `erk docs sync` to regenerate tripwires.md.
    """
    repo_root = require_repo_root(ctx)

    result = promote_tripwire_to_frontmatter(
        project_root=repo_root,
        target_doc_path=target_doc,
        action=action,
        warning=warning,
    )

    if not result.success:
        error_response = PromoteError(
            success=False,
            error=result.error or "Unknown error",
            target_doc_path=target_doc,
        )
        click.echo(json.dumps(asdict(error_response)), err=True)
        raise SystemExit(1)

    if sync_flag:
        # Run erk docs sync (fail-open: don't block on sync failure)
        try:
            subprocess.run(
                ["erk", "docs", "sync"],
                cwd=str(repo_root),
                check=True,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            # erk binary not found or sync failed - non-critical
            pass

    success_response = PromoteSuccess(
        success=True,
        target_doc_path=target_doc,
    )
    click.echo(json.dumps(asdict(success_response)))

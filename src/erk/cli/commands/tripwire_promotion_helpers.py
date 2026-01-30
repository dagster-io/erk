"""Shared helpers for tripwire promotion in land commands.

These helpers are used by `erk land` to extract tripwire candidates
from learn plans and prompt the user to promote them to documentation
frontmatter.
"""

import logging
import subprocess
from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.tripwire_candidates import (
    TripwireCandidate,
    extract_tripwire_candidates_from_comments,
)
from erk_shared.learn.tripwire_promotion import promote_tripwire_to_frontmatter
from erk_shared.output.output import user_output

logger = logging.getLogger(__name__)


def extract_tripwire_candidates_from_learn_plan(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_issue_number: int,
) -> list[TripwireCandidate]:
    """Extract tripwire candidates from a learn plan issue.

    Checks if the issue is a learn plan (has erk-learn label), fetches
    all comments, and reads structured tripwire-candidates metadata.

    Returns empty list on any failure (fail-open).

    Args:
        ctx: ErkContext with issues gateway.
        repo_root: Repository root path.
        plan_issue_number: The plan issue number to check.

    Returns:
        List of TripwireCandidate objects. Empty list if not a learn plan
        or if extraction fails.
    """
    # Check if issue exists
    if not ctx.issues.issue_exists(repo_root, plan_issue_number):
        return []

    issue = ctx.issues.get_issue(repo_root, plan_issue_number)
    if isinstance(issue, IssueNotFound):
        return []

    # Only learn plans have tripwire candidates
    if "erk-learn" not in issue.labels:
        return []

    # Get all comments and scan for tripwire-candidates metadata block
    comments = ctx.issues.get_issue_comments(repo_root, plan_issue_number)
    if not comments:
        logger.debug("No comments on learn plan issue #%d", plan_issue_number)
        return []

    return extract_tripwire_candidates_from_comments(comments)


def prompt_tripwire_promotion(
    ctx: ErkContext,
    *,
    repo_root: Path,
    candidates: list[TripwireCandidate],
    force: bool,
) -> None:
    """Display tripwire candidates and prompt to promote them.

    Shows the candidates in a numbered list, then asks for confirmation.
    In force mode (execute phase), auto-promotes without prompting.

    After promotion, runs `erk docs sync` to regenerate tripwires.md.

    Args:
        ctx: ErkContext with console for prompts.
        repo_root: Repository root path (project root with docs/learned/).
        candidates: List of tripwire candidates to promote.
        force: If True, skip prompt and auto-promote.
    """
    if not candidates:
        return

    user_output("")
    user_output(click.style("Tripwire candidates", bold=True) + f" ({len(candidates)} found):")
    for i, candidate in enumerate(candidates, 1):
        user_output(f"  {i}. [{candidate.target_doc_path}]")
        user_output(f"     Action: {candidate.action}")
        user_output(f"     Warning: {candidate.warning}")

    if not force:
        user_output("")
        if not ctx.console.confirm("Promote these tripwires to documentation?", default=True):
            user_output("Skipped tripwire promotion.")
            return

    # Promote each candidate
    promoted_count = 0
    for candidate in candidates:
        result = promote_tripwire_to_frontmatter(
            project_root=repo_root,
            target_doc_path=candidate.target_doc_path,
            action=candidate.action,
            warning=candidate.warning,
        )
        if result.success:
            promoted_count += 1
        else:
            user_output(
                click.style("⚠ ", fg="yellow")
                + f"Skipped {candidate.target_doc_path}: {result.error}"
            )

    if promoted_count > 0:
        user_output(
            click.style("✓", fg="green")
            + f" Promoted {promoted_count} tripwire(s) to documentation"
        )
        # Run erk docs sync (fail-open)
        _run_docs_sync(repo_root)


def _run_docs_sync(repo_root: Path) -> None:
    """Run erk docs sync to regenerate tripwires.md. Fail-open."""
    try:
        subprocess.run(
            ["erk", "docs", "sync"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        # erk binary not found - non-critical
        logger.debug("erk binary not found, skipping docs sync")
    except subprocess.CalledProcessError:
        # sync failed - non-critical
        logger.debug("erk docs sync failed, skipping")

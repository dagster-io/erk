"""Run a code review using Claude.

This exec command loads a review definition file, assembles the prompt
with boilerplate, and either runs Claude or prints the assembled prompt.

Supports two modes:
- PR mode (--pr-number): Reviews a PR and posts comments to GitHub
- Local mode (--local): Reviews local changes and outputs to stdout

Usage:
    # CI mode (has PR number)
    erk exec run-review --name tripwires --pr-number 123

    # Local mode (before PR exists)
    erk exec run-review --name tripwires --local

    # Local with specific base branch
    erk exec run-review --name tripwires --local --base develop

    # Print assembled prompt without running Claude
    erk exec run-review --name tripwires --pr-number 123 --dry-run

Output:
    In dry-run mode: prints the assembled prompt
    In run mode: invokes Claude CLI with the assembled prompt

Exit Codes:
    0: Success
    1: Review file not found or validation failed

Examples:
    $ erk exec run-review --name tripwires --pr-number 123 --dry-run
    [prints assembled prompt]

    $ erk exec run-review --name tripwires --pr-number 123
    [runs Claude with the prompt]

    $ erk exec run-review --name tripwires --local --dry-run
    [prints assembled prompt for local review]
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click

from erk.review.parsing import parse_review_file
from erk.review.prompt_assembly import assemble_review_prompt
from erk_shared.context.helpers import require_cwd


@dataclass(frozen=True)
class RunReviewError:
    """Error response for run-review command."""

    success: bool
    error_type: str
    message: str


def _get_repository_name(cwd: Path) -> str:
    """Get the repository name (owner/repo) from git remote.

    Args:
        cwd: Current working directory.

    Returns:
        Repository name in owner/repo format.
    """
    # Use gh repo view to get the canonical repo name
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    # Fallback: try to parse from git remote
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        url = result.stdout.strip()
        # Handle git@github.com:owner/repo.git and https://github.com/owner/repo.git
        if url.startswith("git@"):
            # git@github.com:owner/repo.git
            return url.split(":")[-1].replace(".git", "")
        elif "github.com" in url:
            # https://github.com/owner/repo.git
            parts = url.rstrip(".git").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"

    return "unknown/unknown"


def _get_trunk_branch(cwd: Path) -> str:
    """Auto-detect the trunk branch (main or master).

    Args:
        cwd: Current working directory.

    Returns:
        The detected trunk branch name ("main" or "master").
    """
    # Check if 'main' branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "main"],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        return "main"

    # Fallback to 'master'
    return "master"


@click.command(name="run-review")
@click.option("--name", "review_name", required=True, help="Review filename (without .md)")
@click.option("--pr-number", type=int, help="PR number to review (mutually exclusive with --local)")
@click.option(
    "--local",
    "is_local",
    is_flag=True,
    help="Run in local mode (reviews local changes, outputs to stdout)",
)
@click.option(
    "--base",
    "base_branch",
    help="Base branch for local mode diff (default: auto-detect main/master)",
)
@click.option(
    "--reviews-dir",
    default=".github/reviews",
    help="Directory containing review definitions (default: .github/reviews)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print assembled prompt without running Claude",
)
@click.pass_context
def run_review(
    ctx: click.Context,
    review_name: str,
    pr_number: int | None,
    is_local: bool,
    base_branch: str | None,
    reviews_dir: str,
    dry_run: bool,
) -> None:
    """Run a code review using Claude.

    Loads the specified review definition, assembles the prompt with
    standard boilerplate, and either prints it (--dry-run) or runs
    Claude with the prompt.

    REVIEW_NAME: Name of the review file (e.g., "tripwires" for tripwires.md)
    """
    cwd = require_cwd(ctx)

    # Validate mode flags
    if pr_number is not None and is_local:
        error = RunReviewError(
            success=False,
            error_type="invalid_flags",
            message="Cannot specify both --pr-number and --local",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(1)

    if pr_number is None and not is_local:
        error = RunReviewError(
            success=False,
            error_type="invalid_flags",
            message="Must specify either --pr-number or --local",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(1)

    if base_branch is not None and not is_local:
        error = RunReviewError(
            success=False,
            error_type="invalid_flags",
            message="--base can only be used with --local",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(1)

    reviews_path = cwd / reviews_dir

    # Construct the review file path
    review_file = reviews_path / f"{review_name}.md"

    # Parse and validate the review file
    result = parse_review_file(review_file)

    if not result.is_valid:
        error = RunReviewError(
            success=False,
            error_type="validation_failed",
            message=f"Review file validation failed: {', '.join(result.errors)}",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(1)

    assert result.parsed_review is not None
    review = result.parsed_review

    # Get repository name
    repository = _get_repository_name(cwd)

    # Determine the effective base branch for local mode
    effective_base_branch: str | None = None
    if is_local:
        effective_base_branch = base_branch if base_branch is not None else _get_trunk_branch(cwd)

    # Assemble the prompt
    prompt = assemble_review_prompt(
        review=review,
        repository=repository,
        pr_number=pr_number,
        base_branch=effective_base_branch,
    )

    if dry_run:
        # Print the assembled prompt
        click.echo(prompt)
        return

    # Run Claude with the prompt
    claude_cmd = [
        "claude",
        "--print",
        "--model",
        review.frontmatter.model,
        "--allowedTools",
        review.frontmatter.allowed_tools,
        "--dangerously-skip-permissions",
        "--output-format",
        "stream-json",
        "--verbose",
        prompt,
    ]

    # Execute Claude - use subprocess.run with stdin=subprocess.DEVNULL
    # to avoid any interactive prompts
    result_proc = subprocess.run(
        claude_cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        check=False,
    )

    # Exit with Claude's exit code
    raise SystemExit(result_proc.returncode)

"""Run a code review using Claude.

This exec command loads a review definition file, assembles the prompt
with boilerplate, and either runs Claude or prints the assembled prompt.

Usage:
    erk exec run-review --name tripwires --pr-number 123

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


@click.command(name="run-review")
@click.option("--name", "review_name", required=True, help="Review filename (without .md)")
@click.option("--pr-number", required=True, type=int, help="PR number to review")
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
    pr_number: int,
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

    # Assemble the prompt
    prompt = assemble_review_prompt(
        review=review,
        repository=repository,
        pr_number=pr_number,
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

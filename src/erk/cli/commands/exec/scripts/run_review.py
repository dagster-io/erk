"""Run a code review using Claude.

This exec command loads a review definition file, assembles the prompt
with boilerplate, and either runs Claude or prints the assembled prompt.

Supports two modes:
- PR mode (--pr-number): Reviews an existing PR, posts comments to GitHub
- Local mode (--local): Reviews local changes vs base branch, outputs to stdout

Usage:
    # CI mode (has PR number)
    erk exec run-review --name tripwires --pr-number 123

    # Local mode (before PR exists)
    erk exec run-review --name tripwires --local

    # Local mode with specific base branch
    erk exec run-review --name tripwires --local --base develop

    # Print assembled prompt without running Claude
    erk exec run-review --name tripwires --pr-number 123 --dry-run

Output:
    In dry-run mode: prints the assembled prompt
    In run mode: invokes Claude CLI with the assembled prompt

Exit Codes:
    0: Success
    1: Review file not found or validation failed
    2: Invalid flag combination

Examples:
    $ erk exec run-review --name tripwires --pr-number 123 --dry-run
    [prints assembled prompt]

    $ erk exec run-review --name tripwires --local --dry-run
    [prints local review prompt]

    $ erk exec run-review --name tripwires --pr-number 123
    [runs Claude with the prompt]
"""

import json
from dataclasses import dataclass

import click

from erk.review.parsing import parse_review_file
from erk.review.prompt_assembly import assemble_review_prompt
from erk_shared.context.helpers import (
    get_repo_identifier,
    require_claude_executor,
    require_cwd,
    require_git,
)


@dataclass(frozen=True)
class RunReviewError:
    """Error response for run-review command."""

    success: bool
    error_type: str
    message: str


@click.command(name="run-review")
@click.option("--name", "review_name", required=True, help="Review filename (without .md)")
@click.option("--pr-number", type=int, help="PR number to review (PR mode)")
@click.option("--local", "local_mode", is_flag=True, help="Review local changes (local mode)")
@click.option("--base", "base_branch", help="Base branch for local mode (default: auto-detect)")
@click.option(
    "--reviews-dir",
    default=".claude/reviews",
    help="Directory containing review definitions (default: .claude/reviews)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print assembled prompt without running Claude",
)
@click.pass_context
def run_review(
    ctx: click.Context,
    *,
    review_name: str,
    pr_number: int | None,
    local_mode: bool,
    base_branch: str | None,
    reviews_dir: str,
    dry_run: bool,
) -> None:
    """Run a code review using Claude.

    Loads the specified review definition, assembles the prompt with
    standard boilerplate, and either prints it (--dry-run) or runs
    Claude with the prompt.

    Supports two modes:
    - PR mode (--pr-number): Reviews an existing PR
    - Local mode (--local): Reviews local changes vs base branch

    REVIEW_NAME: Name of the review file (e.g., "tripwires" for tripwires.md)
    """
    cwd = require_cwd(ctx)

    # Validate mode flags
    if pr_number is not None and local_mode:
        error = RunReviewError(
            success=False,
            error_type="invalid_flags",
            message="Cannot specify both --pr-number and --local",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(2)

    if pr_number is None and not local_mode:
        error = RunReviewError(
            success=False,
            error_type="invalid_flags",
            message="Must specify either --pr-number or --local",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(2)

    if base_branch is not None and not local_mode:
        error = RunReviewError(
            success=False,
            error_type="invalid_flags",
            message="--base can only be used with --local",
        )
        click.echo(json.dumps(error.__dict__, indent=2), err=True)
        raise SystemExit(2)

    # For local mode, auto-detect base branch if not specified
    resolved_base_branch: str | None = None
    if local_mode:
        resolved_base_branch = (
            base_branch if base_branch else require_git(ctx).branch.detect_trunk_branch(cwd)
        )

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

    # Get repository name from context
    repository = get_repo_identifier(ctx)
    if repository is None:
        repository = "unknown/unknown"

    # Assemble the prompt
    prompt = assemble_review_prompt(
        review=review,
        repository=repository,
        pr_number=pr_number,
        base_branch=resolved_base_branch,
    )

    if dry_run:
        # Print the assembled prompt
        click.echo(prompt)
        return

    # Use ClaudeExecutor gateway for execution
    executor = require_claude_executor(ctx)

    # Parse allowed_tools from comma-separated string
    tools: list[str] | None = None
    if review.frontmatter.allowed_tools:
        tools = [t.strip() for t in review.frontmatter.allowed_tools.split(",")]

    exit_code = executor.execute_prompt_passthrough(
        prompt,
        model=review.frontmatter.model,
        tools=tools,
        cwd=cwd,
        dangerous=True,
    )

    raise SystemExit(exit_code)

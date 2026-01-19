"""Discover reviews matching PR changed files.

This exec command discovers code review definitions that match
the files changed in a pull request.

Usage:
    erk exec discover-reviews --pr-number 123

    # Use custom reviews directory
    erk exec discover-reviews --pr-number 123 --reviews-dir .github/reviews

Output:
    JSON with matching reviews, skipped reviews, and validation errors

Exit Codes:
    0: Discovery succeeded (even if no reviews match)
    1: Discovery failed (validation errors preventing operation)

Examples:
    $ erk exec discover-reviews --pr-number 123
    {
      "success": true,
      "reviews": [
        {"name": "Tripwires Review", "marker": "<!-- tripwires-review -->", ...}
      ],
      "skipped": ["review-c.md"],
      "disabled": ["review-d.md"],
      "matrix": {"include": [...]}
    }
"""

import json
from dataclasses import dataclass

import click

from erk.review.parsing import ParsedReview, discover_matching_reviews
from erk_shared.context.helpers import require_cwd
from erk_shared.subprocess_utils import run_subprocess_with_context


@dataclass(frozen=True)
class DiscoverySuccess:
    """Success response for review discovery."""

    success: bool
    reviews: list[dict[str, object]]
    skipped: list[str]
    disabled: list[str]
    matrix: dict[str, list[dict[str, str]]]


@dataclass(frozen=True)
class DiscoveryError:
    """Error response for review discovery."""

    success: bool
    error_type: str
    message: str
    validation_errors: dict[str, list[str]]


def _get_pr_changed_files(pr_number: int) -> list[str]:
    """Get list of files changed in a PR.

    Uses gh pr diff --name-only to retrieve the file list.

    Args:
        pr_number: PR number to query.

    Returns:
        List of file paths changed in the PR.
    """
    result = run_subprocess_with_context(
        cmd=["gh", "pr", "diff", str(pr_number), "--name-only"],
        operation_context=f"get changed files for PR #{pr_number}",
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def _review_to_dict(review: ParsedReview) -> dict[str, object]:
    """Convert a ParsedReview to a JSON-serializable dict."""
    return {
        "name": review.frontmatter.name,
        "filename": review.filename,
        "marker": review.frontmatter.marker,
        "model": review.frontmatter.model,
        "timeout_minutes": review.frontmatter.timeout_minutes,
        "allowed_tools": review.frontmatter.allowed_tools,
        "paths": list(review.frontmatter.paths),
    }


def _create_matrix(reviews: list[ParsedReview]) -> dict[str, list[dict[str, str]]]:
    """Create GitHub Actions matrix format from reviews.

    The matrix format allows running each review as a parallel job.

    Args:
        reviews: List of parsed reviews.

    Returns:
        Matrix dict with "include" key for GitHub Actions.
    """
    include = [
        {
            "name": review.frontmatter.name,
            "filename": review.filename,
        }
        for review in reviews
    ]
    return {"include": include}


@click.command(name="discover-reviews")
@click.option("--pr-number", required=True, type=int, help="PR number to analyze")
@click.option(
    "--reviews-dir",
    default=".github/reviews",
    help="Directory containing review definitions (default: .github/reviews)",
)
@click.pass_context
def discover_reviews(
    ctx: click.Context,
    pr_number: int,
    reviews_dir: str,
) -> None:
    """Discover code reviews matching PR changed files.

    Parses all review definition files in the reviews directory,
    validates them, and returns those whose path patterns match
    at least one file changed in the PR.

    Output is JSON suitable for GitHub Actions matrix jobs.
    """
    cwd = require_cwd(ctx)
    reviews_path = cwd / reviews_dir

    # Get files changed in the PR
    try:
        changed_files = _get_pr_changed_files(pr_number)
    except RuntimeError as e:
        result = DiscoveryError(
            success=False,
            error_type="pr_fetch_failed",
            message=f"Failed to get PR changed files: {e}",
            validation_errors={},
        )
        click.echo(json.dumps(result.__dict__, indent=2))
        raise SystemExit(1) from None

    # Discover matching reviews
    discovery = discover_matching_reviews(
        reviews_dir=reviews_path,
        changed_files=changed_files,
    )

    # Check for validation errors
    if discovery.errors:
        result = DiscoveryError(
            success=False,
            error_type="validation_failed",
            message=f"Validation failed for {len(discovery.errors)} review file(s)",
            validation_errors={k: list(v) for k, v in discovery.errors.items()},
        )
        click.echo(json.dumps(result.__dict__, indent=2))
        raise SystemExit(1)

    # Build success response
    reviews_list = [_review_to_dict(r) for r in discovery.reviews]
    matrix = _create_matrix(list(discovery.reviews))

    success_result = DiscoverySuccess(
        success=True,
        reviews=reviews_list,
        skipped=list(discovery.skipped),
        disabled=list(discovery.disabled),
        matrix=matrix,
    )
    click.echo(json.dumps(success_result.__dict__, indent=2))

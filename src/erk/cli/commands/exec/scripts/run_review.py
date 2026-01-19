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

from erk.review.parsing import ParsedReview, parse_review_file
from erk_shared.context.helpers import require_cwd

# Boilerplate template injected around review body
REVIEW_PROMPT_TEMPLATE = """\
REPO: {repository}
PR NUMBER: {pr_number}

## Task

{review_name}: Review code changes.

## Step 1: Review-Specific Instructions

{review_body}

## Step 2: Get Existing Review Comment

Fetch the existing review comment to preserve the activity log:

```
gh pr view {pr_number} --json comments \\
  --jq '.comments[] | select(.body | contains("{marker}")) | .body'
```

If a comment exists, extract the Activity Log section (everything after
`### Activity Log`). You will append to this log.

## Step 3: Get the Diff

```
gh pr diff {pr_number} --name-only
gh pr diff {pr_number}
```

## Step 4: Post Inline Comments for Violations

**IMPORTANT: Post an inline comment for EACH violation found.**

```
erk exec post-pr-inline-comment \\
  --pr-number {pr_number} \\
  --path "path/to/file" \\
  --line LINE_NUMBER \\
  --body "**{review_name}**: [pattern detected] - [why it's a problem] - [fix suggestion]"
```

## Step 5: Post Summary Comment

**IMPORTANT: All timestamps MUST be in Pacific Time (PT), NOT UTC.**

Get the current Pacific time timestamp:

```
TZ='America/Los_Angeles' date '+%Y-%m-%d %H:%M:%S'
```

Post/update the summary comment:

```
erk exec post-or-update-pr-summary \\
  --pr-number {pr_number} \\
  --marker "{marker}" \\
  --body "SUMMARY_TEXT"
```

Summary format (preserve existing Activity Log entries and prepend new entry):

```
{marker}

## ✅ {review_name}   (use ✅ if 0 violations, ❌ if 1+ violations)

**Last updated:** YYYY-MM-DD HH:MM:SS PT

Found X violations across Y files. Inline comments posted for each.

### Patterns Checked
✅ [pattern] - None found
❌ [pattern] - Found in src/foo.py:12

(Use ✅ when compliant, ❌ when violation found.)

### Violations Summary
- `file.py:123`: [brief description]

### Files Reviewed
- `file.py`: N violations
- `file.sh`: N violations

---

### Activity Log
- **YYYY-MM-DD HH:MM:SS PT**: [Brief description of this review's findings]
- [Previous log entries preserved here...]
```

Activity log entry examples:
- "Found 2 violations (bare subprocess.run in x.py, /tmp/ usage in y.py)"
- "All violations resolved"
- "No violations detected"

Keep the last 10 log entries maximum.
"""


@dataclass(frozen=True)
class RunReviewError:
    """Error response for run-review command."""

    success: bool
    error_type: str
    message: str


def _assemble_review_prompt(
    *,
    review: ParsedReview,
    repository: str,
    pr_number: int,
) -> str:
    """Assemble a complete review prompt from a review definition.

    Injects the review body into the boilerplate template with
    repository and PR context.

    Args:
        review: The parsed review definition.
        repository: Repository name (e.g., "owner/repo").
        pr_number: PR number being reviewed.

    Returns:
        Complete prompt string ready for Claude.
    """
    return REVIEW_PROMPT_TEMPLATE.format(
        repository=repository,
        pr_number=pr_number,
        review_name=review.frontmatter.name,
        review_body=review.body,
        marker=review.frontmatter.marker,
    )


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
    prompt = _assemble_review_prompt(
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

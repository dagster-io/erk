"""Prompt assembly for code reviews.

This module injects standard boilerplate around review-specific instructions
to create a complete prompt for Claude to execute.
"""

from erk.review.models import ParsedReview

# PR mode template: posts comments to GitHub
PR_REVIEW_PROMPT_TEMPLATE = """\
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

# Local mode template: outputs to stdout instead of posting to GitHub
LOCAL_REVIEW_PROMPT_TEMPLATE = """\
REPO: {repository}
BASE BRANCH: {base_branch}

## Task

{review_name}: Review code changes.

## Step 1: Review-Specific Instructions

{review_body}

## Step 2: Get the Diff

Get the list of changed files and their contents compared to the base branch:

```
git diff --name-only $(git merge-base {base_branch} HEAD)...HEAD
git diff $(git merge-base {base_branch} HEAD)...HEAD
```

## Step 3: Output Violations

For EACH violation found, output a structured violation report to stdout:

```
--- VIOLATION ---
File: path/to/file
Line: LINE_NUMBER
Pattern: [pattern name]
Issue: [why it's a problem]
Fix: [fix suggestion]
--- END VIOLATION ---
```

At the end, output a summary:

```
--- SUMMARY ---
{review_name}
Total violations: N
Files checked: N

Patterns Checked:
✅ [pattern] - None found
❌ [pattern] - Found in src/foo.py:12

Violations by File:
- file.py: N violations
- file.sh: N violations
--- END SUMMARY ---
```
"""


def assemble_review_prompt(
    *,
    review: ParsedReview,
    repository: str,
    pr_number: int | None,
    base_branch: str | None,
) -> str:
    """Assemble a complete review prompt from a review definition.

    Injects the review body into the appropriate template (PR mode or local mode)
    with repository context.

    Args:
        review: The parsed review definition.
        repository: Repository name (e.g., "owner/repo").
        pr_number: PR number being reviewed (for PR mode).
        base_branch: Base branch for diff (for local mode).

    Returns:
        Complete prompt string ready for Claude.

    Raises:
        ValueError: If both pr_number and base_branch are provided,
            or if neither is provided.
    """
    if pr_number is not None and base_branch is not None:
        raise ValueError("Cannot specify both pr_number and base_branch")
    if pr_number is None and base_branch is None:
        raise ValueError("Must specify either pr_number or base_branch")

    if pr_number is not None:
        # PR mode: use PR template with GitHub integration
        return PR_REVIEW_PROMPT_TEMPLATE.format(
            repository=repository,
            pr_number=pr_number,
            review_name=review.frontmatter.name,
            review_body=review.body,
            marker=review.frontmatter.marker,
        )
    else:
        # Local mode: use local template with stdout output
        return LOCAL_REVIEW_PROMPT_TEMPLATE.format(
            repository=repository,
            base_branch=base_branch,
            review_name=review.frontmatter.name,
            review_body=review.body,
        )

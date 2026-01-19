"""Prompt assembly for code reviews.

This module injects standard boilerplate around review-specific instructions
to create a complete prompt for Claude to execute.
"""

from erk.review.models import ParsedReview

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


def assemble_review_prompt(
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

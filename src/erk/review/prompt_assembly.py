"""Prompt assembly for code reviews.

This module injects standard boilerplate around review-specific instructions
to create a complete prompt for Claude to execute.

Supports two modes:
- PR mode: Reviews an existing pull request, posts comments to GitHub
- Local mode: Reviews uncommitted changes locally, outputs to stdout
"""

from erk.review.models import ParsedReview

# Boilerplate template for PR reviews (posts comments to GitHub)
REVIEW_PROMPT_TEMPLATE = """\
REPO: {repository}
PR NUMBER: {pr_number}

## Task

{review_name}: Review code changes.

## Step 1: Review-Specific Instructions

{review_body}

## Step 2: Get Existing Activity Log

Fetch the existing activity log to preserve prior entries:

```
erk exec get-review-activity-log --pr-number {pr_number} --marker "{marker}"
```

This returns JSON with `activity_log` (the text after `### Activity Log` from
any existing summary comment). If `found` is false, start a fresh log.

## Step 3: Get the Diff

```
gh pr diff {pr_number} --name-only
gh pr diff {pr_number}
```

## Step 4: Collect Violations (analysis only — DO NOT post comments)

Analyze the diff from Step 3. Build a numbered list of ALL violations found.
Each entry must include: path, line number, and comment body.

Example output format:

```
Violations found:
1. path=src/foo.py line=42 body="**{review_name}**: bare subprocess.run call - use wrapper"
2. path=src/bar.py line=10 body="**{review_name}**: /tmp/ path usage - use tempfile"
```

**DO NOT post any comments in this step.** Only collect and list them.

## Step 5: Deduplicate Against Existing Comments

Fetch all existing review comments:

```
erk exec get-pr-review-comments --pr {pr_number} --include-resolved
```

This returns JSON with a `threads` array. Each thread has `path`, `line`,
and `comments` (each with `body`).

For EACH violation collected in Step 4, check against existing comments.
A violation is a DUPLICATE if an existing comment matches ALL of:
1. Same file path
2. Same line (or within ±2 lines, to handle diff shifts)
3. Starts with the same review prefix (`**{review_name}**:`)
4. First 80 characters of the body match

**You MUST output the dedup decision for EVERY violation:**

```
Dedup results:
1. src/foo.py:42 — NEW (no matching existing comment)
2. src/bar.py:10 — DUPLICATE (matches existing comment on line 11)
```

If you skip this output, dedup has failed. Every violation MUST appear with
a NEW or DUPLICATE label.

## Step 6: Post Only NEW Violations

For each violation marked NEW in Step 5, post an inline comment:

```
erk exec post-pr-inline-comment \\
  --pr-number {pr_number} \\
  --path "path/to/file" \\
  --line LINE_NUMBER \\
  --body "**{review_name}**: [pattern detected] - [rule/doc reference]"
```

Do NOT post violations marked DUPLICATE. Log the count of skipped duplicates
for the summary (e.g., "Skipped 2 duplicate comments").

## Step 7: Post Summary Comment

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

<details>
<summary>Details</summary>

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

</details>
```

Activity log entry examples:
- "Found 2 violations (bare subprocess.run in x.py, /tmp/ usage in y.py)"
- "All violations resolved"
- "No violations detected"

Keep the last 10 log entries maximum.
"""

# Local review template (outputs violations to stdout, no PR interaction)
LOCAL_REVIEW_PROMPT_TEMPLATE = """\
REPO: {repository}
BASE BRANCH: {base_branch}

## Task

{review_name}: Review local code changes (pre-PR review).

## Step 1: Review-Specific Instructions

{review_body}

## Step 2: Get the Diff

Get the list of changed files and their contents:

```
git diff --name-only $(git merge-base {base_branch} HEAD)...HEAD
git diff $(git merge-base {base_branch} HEAD)...HEAD
```

## Step 3: Output Violations

For EACH violation found, output to stdout in this format:

```
**{review_name} Violation**
- File: path/to/file.py
- Line: LINE_NUMBER
- Issue: [pattern detected]
- Rule: [rule/doc reference]

---
```

At the end, output a summary:

```
## Summary

Found X violations across Y files.

### Patterns Checked
✅ [pattern] - None found
❌ [pattern] - Found in src/foo.py:12

### Files Reviewed
- file.py: N violations
- file.sh: N violations
```
"""


EXCLUDE_SECTION = """\


## File Exclusions

The following file patterns are excluded from review. Do NOT analyze, flag violations,
or post inline comments for any files matching these patterns:

{patterns}

Skip these files entirely when reviewing the diff.
"""


def _build_exclude_section(exclude_patterns: tuple[str, ...]) -> str:
    """Build the file exclusion section for injection into prompts.

    Args:
        exclude_patterns: Gitignore-style glob patterns to exclude.

    Returns:
        Formatted exclusion section, or empty string if no patterns.
    """
    if not exclude_patterns:
        return ""

    pattern_list = "\n".join(f"- `{p}`" for p in exclude_patterns)
    return EXCLUDE_SECTION.format(patterns=pattern_list)


def assemble_review_prompt(
    *,
    review: ParsedReview,
    repository: str,
    pr_number: int | None,
    base_branch: str | None,
    exclude_patterns: tuple[str, ...] = (),
) -> str:
    """Assemble a complete review prompt from a review definition.

    Supports two modes:
    - PR mode (pr_number provided): Reviews an existing PR, posts comments
    - Local mode (base_branch provided): Reviews local changes, outputs to stdout

    Args:
        review: The parsed review definition.
        repository: Repository name (e.g., "owner/repo").
        pr_number: PR number being reviewed (for PR mode).
        base_branch: Base branch for diff comparison (for local mode).

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

    exclude_section = _build_exclude_section(exclude_patterns)

    if pr_number is not None:
        prompt = REVIEW_PROMPT_TEMPLATE.format(
            repository=repository,
            pr_number=pr_number,
            review_name=review.frontmatter.name,
            review_body=review.body,
            marker=review.frontmatter.marker,
        )
        if exclude_section:
            # Inject after "Get the Diff" step
            prompt = prompt.replace(
                "## Step 4: Collect Violations",
                exclude_section + "## Step 4: Collect Violations",
            )
        return prompt

    # Local mode
    assert base_branch is not None
    prompt = LOCAL_REVIEW_PROMPT_TEMPLATE.format(
        repository=repository,
        base_branch=base_branch,
        review_name=review.frontmatter.name,
        review_body=review.body,
    )
    if exclude_section:
        # Inject after "Get the Diff" step
        prompt = prompt.replace(
            "## Step 3: Output Violations",
            exclude_section + "## Step 3: Output Violations",
        )
    return prompt

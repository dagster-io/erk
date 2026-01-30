---
title: Review Prompt Assembly
read_when:
  - "modifying review prompt generation"
  - "understanding the PR review vs local review modes"
  - "working with src/erk/review/prompt_assembly.py"
tripwires:
  - action: "adding a new review mode without updating assemble_review_prompt validation"
    warning: "The function validates mutual exclusivity of pr_number and base_branch. New modes must fit within or extend this validation."
---

# Review Prompt Assembly

The review system assembles prompts for AI-driven code review. It supports two mutually exclusive modes and a structured 6-step review process.

## Two-Mode System

`assemble_review_prompt()` operates in exactly one of two modes:

| Mode           | Parameter              | Purpose                    | Output Target                   |
| -------------- | ---------------------- | -------------------------- | ------------------------------- |
| **PR Mode**    | `pr_number` provided   | Review a submitted PR      | Posts inline comments to GitHub |
| **Local Mode** | `base_branch` provided | Review uncommitted changes | Outputs to terminal             |

The function raises `ValueError` if both or neither parameter is provided — the modes are mutually exclusive.

## PR Mode

When `pr_number` is provided:

- Generates a prompt that instructs the AI to post inline review comments
- Includes deduplication instructions (see [Inline Comment Deduplication](inline-comment-deduplication.md))
- Targets specific file paths and line numbers from the PR diff

## Local Mode

When `base_branch` is provided:

- Generates a prompt for reviewing uncommitted local changes
- Outputs findings to the terminal rather than GitHub
- Compares working tree against the specified base branch

## Prompt Structure

Both modes follow a 6-step review process embedded in the template:

1. Understand the review's focus areas (from review frontmatter)
2. Analyze the diff/changes
3. Identify issues matching the review criteria
4. Deduplicate against existing comments (PR mode only)
5. Format findings as inline comments or terminal output
6. Provide summary assessment

## Parameter Validation

The function uses LBYL to validate mode selection:

```python
if pr_number is not None and base_branch is not None:
    raise ValueError("Cannot specify both pr_number and base_branch")
if pr_number is None and base_branch is None:
    raise ValueError("Must specify either pr_number or base_branch")
```

## Reference Implementation

`src/erk/review/prompt_assembly.py`:

- `assemble_review_prompt()` (lines 194–241): Main entry point
- `REVIEW_PROMPT_TEMPLATE`: PR mode template
- `LOCAL_REVIEW_PROMPT_TEMPLATE`: Local mode template

## Related Documentation

- [Inline Comment Deduplication](inline-comment-deduplication.md) — Deduplication algorithm used in PR mode
- [PR Operations Skill](../../.claude/skills/pr-operations/SKILL.md) — Commands for managing PR review threads

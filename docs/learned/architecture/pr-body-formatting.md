---
title: PR Body Formatting Pattern
read_when:
  - "adding GitHub-specific enhancements to PR descriptions"
  - "understanding separation between git commit messages and PR bodies"
  - "implementing badges, metadata, or HTML in PR bodies"
  - "debugging why HTML appears in git commit messages"
tripwires:
  - action: "adding HTML, badges, or GitHub-specific markup to commit messages"
    warning: "Use the two-target pattern: plain text pr_body for commits, enhanced pr_body_for_github for the PR. Never put GitHub-specific HTML into git commit messages."
---

# PR Body Formatting Pattern

This document describes the two-target pattern for PR body formatting, which separates plain-text commit messages from GitHub-enhanced PR descriptions.

## The Problem

Git commit messages and GitHub PR bodies serve different audiences:

- **Commit messages**: Plain text, permanent git history, read by `git log`
- **PR bodies**: Rich HTML/Markdown, temporary PR metadata, read on GitHub web UI

When we want to enhance PR bodies with GitHub-specific features (HTML tags, badges, embedded plans), we must ensure these enhancements never pollute the git commit message.

## The Two-Target Pattern

### Pattern Overview

Maintain **two separate body strings** during PR submission:

1. **`pr_body`**: Plain text description (goes into git commit message)
2. **`pr_body_for_github`**: Enhanced description with HTML/metadata (sent to GitHub PR API)

### When to Use

Use this pattern when adding any GitHub-specific enhancement to PR bodies:

- HTML tags (`<details>`, `<summary>`, `<img>`, etc.)
- GitHub-specific markdown (badges, mentions, issue links)
- Embedded metadata (plans, test results, CI status)
- Any content that should be visible on GitHub but not in git history

## Implementation Reference

### Location

`src/erk/cli/commands/pr/submit_pipeline.py:633-636`

### Code Example

```python
# Start with plain text body
pr_body = "Summary of changes"

# Embed plan in PR body if available (not in commit message)
pr_body_for_github = pr_body
if state.plan_context is not None:
    pr_body_for_github = pr_body + _build_plan_details_section(state.plan_context)

# Build footer and combine
metadata_section = build_pr_body_footer(
    pr_number=state.pr_number,
    issue_number=issue_number,
    plans_repo=effective_plans_repo,
)
final_body = pr_body_for_github + metadata_section

# Update PR metadata (uses enhanced body)
ctx.github.update_pr_title_and_body(
    repo_root=state.repo_root,
    pr_number=state.pr_number,
    title=pr_title,
    body=BodyText(content=final_body),
)

# Later: amend commit message (uses plain body)
ctx.git.commit.amend(
    repo_root=state.repo_root,
    message=f"{pr_title}\n\n{pr_body}",
)
```

## Key Principles

### 1. Start with Plain Text

Always construct the base `pr_body` as plain text first. This becomes the commit message content.

```python
pr_body = "Summary of changes"  # Plain text, no HTML
```

### 2. Clone Before Enhancement

Create a separate variable for GitHub-specific content:

```python
pr_body_for_github = pr_body  # Start identical
pr_body_for_github = pr_body_for_github + html_content  # Add GitHub features
```

### 3. Route to Correct Target

- Commit messages: Use `pr_body` (plain text)
- GitHub PR API: Use `pr_body_for_github` (enhanced)

### 4. Never Mix

Once you've created `pr_body_for_github`, never use it for commit messages. The separation is absolute.

## Anti-Pattern: Putting HTML in Commit Messages

**WRONG:**

```python
# BAD: HTML in commit message
pr_body = "Summary\n\n<details>Plan here</details>"
ctx.git.commit.amend(message=f"{pr_title}\n\n{pr_body}")
```

This results in:

```
Add feature

Summary

<details>Plan here</details>
```

in `git log`, which is permanent pollution.

**CORRECT:**

```python
# GOOD: Separate targets
pr_body = "Summary"
pr_body_for_github = pr_body + "\n\n<details>Plan here</details>"

ctx.git.commit.amend(message=f"{pr_title}\n\n{pr_body}")
ctx.github.update_pr_title_and_body(body=BodyText(content=pr_body_for_github))
```

## Example Use Case: Plan Embedding

Plan embedding is the primary use case for this pattern. See [Plan Embedding in PR](../pr-operations/plan-embedding-in-pr.md) for complete details.

```python
# Plain body for commit message
pr_body = "Summary of changes"

# Enhanced body with plan for GitHub
pr_body_for_github = pr_body
if state.plan_context is not None:
    plan_section = _build_plan_details_section(state.plan_context)
    pr_body_for_github = pr_body + plan_section
```

The `<details>` block with the plan content appears in the GitHub PR but not in git history.

## Tripwire

**NEVER** put GitHub-specific HTML into git commit messages. Use the two-target pattern to separate plain-text commit content from GitHub-enhanced PR descriptions.

## Related Documentation

- [Plan Embedding in PR](../pr-operations/plan-embedding-in-pr.md) - Primary use case
- [PR Submit Phases](../pr-operations/pr-submit-phases.md) - Where this pattern is used
- [Commit Message Format](../erk-dev/commit-message-format.md) - Git commit standards

# Embed Plan in PR Description via `<details>` Tag

## Summary

When a PR is linked to an erk-plan issue, embed the full plan markdown directly in the PR body inside a collapsed `<details>` block. This makes the plan visible to reviewers without cluttering the PR description.

## Target PR Body Structure

```markdown
[AI-generated summary]

<details>
<summary><strong>Implementation Plan</strong> (Issue #1234)</summary>

[raw plan markdown from plan_context.plan_content]
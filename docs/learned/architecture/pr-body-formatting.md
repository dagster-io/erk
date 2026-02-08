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

## Why Two Targets Matter

Git commit messages are **permanent immutable records** in git history, readable via `git log` by anyone with the repository, forever. GitHub PR bodies are **ephemeral GitHub-specific metadata** that only exists in the PR API and web UI.

When we want GitHub-specific enhancements (HTML tags, badges, collapsible sections), we must ensure they never leak into git history. HTML in commit messages is permanent pollution — it can't be removed without rewriting history.

## The Pattern: Two Variables, Two Destinations

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, finalize_pr function -->

Maintain two separate body strings throughout PR submission (see `finalize_pr()` at `src/erk/cli/commands/pr/submit_pipeline.py:603`):

1. **`pr_body`** — Plain text only, used for `git commit --amend` (line 663)
2. **`pr_body_for_github`** — Start as clone of `pr_body`, then append HTML/metadata, used for GitHub PR API (line 653)

The split happens **before** any GitHub-specific content is added. The plain `pr_body` is cloned into `pr_body_for_github`, then only the GitHub version receives enhancements.

## Decision Table: When to Use This Pattern

| Adding to PR                           | Use Two-Target Pattern? | Reason                            |
| -------------------------------------- | ----------------------- | --------------------------------- |
| HTML tags (`<details>`, `<img>`, etc.) | ✅ Required             | HTML doesn't belong in git log    |
| GitHub badges (shields.io URLs)        | ✅ Required             | Image markdown is GitHub-specific |
| Issue closing keywords                 | ❌ Not needed           | "Closes #123" is valid in both    |
| Plain text summary                     | ❌ Not needed           | Same content for both targets     |
| Embedded plan content                  | ✅ Required             | Uses `<details>` HTML wrapper     |
| PR metadata footer                     | ✅ Required             | GitHub-only metadata section      |

## Implementation Invariants

1. **`pr_body` is created first** — always construct the plain text body before any GitHub enhancements
2. **Clone, don't mutate** — `pr_body_for_github = pr_body` creates the split point; `pr_body` never changes after this
3. **Route to correct destination** — commit messages use `pr_body`, GitHub API calls use `pr_body_for_github`
4. **Never cross-contaminate** — once `pr_body_for_github` has HTML, it never touches git operations

## Anti-Pattern: Single-Variable Mutation

**WRONG** (the bug this pattern prevents):

```python
# Start with plain text
pr_body = "Summary of changes"

# Mistake: mutating the only body variable
pr_body = pr_body + "\n\n<details>Plan here</details>"

# Both destinations now get HTML
ctx.git.commit.amend_commit(repo_root, f"{title}\n\n{pr_body}")  # ❌ HTML in git log
ctx.github.update_pr_title_and_body(..., body=BodyText(content=pr_body))  # ✅ OK
```

Result: HTML permanently embedded in git commit history.

**CORRECT** (two-variable pattern):

```python
# Start with plain text
pr_body = "Summary of changes"

# Clone for GitHub enhancements
pr_body_for_github = pr_body
pr_body_for_github = pr_body_for_github + "\n\n<details>Plan here</details>"

# Each destination gets the right version
ctx.git.commit.amend_commit(repo_root, f"{title}\n\n{pr_body}")  # ✅ Plain text only
ctx.github.update_pr_title_and_body(..., body=BodyText(content=pr_body_for_github))  # ✅ Enhanced
```

## Real-World Usage: Plan Embedding

The primary use case is embedding plan content in PRs without polluting git history. See [Plan Embedding in PR](../pr-operations/plan-embedding-in-pr.md) for the full workflow.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _build_plan_details_section -->

The `_build_plan_details_section()` function (line 587) wraps plan markdown in a `<details>` tag. This HTML is appended only to `pr_body_for_github` (line 638), never to `pr_body`.

When the commit is amended (line 664), it uses `pr_body` without the plan HTML. When the PR metadata is updated via GitHub API (line 649), it uses `pr_body_for_github` with the collapsible plan section.

## Related Documentation

- [Plan Embedding in PR](../pr-operations/plan-embedding-in-pr.md) — Primary use case for this pattern
- [PR Submit Phases](../pr-operations/pr-submit-phases.md) — Where PR body assembly happens in the pipeline

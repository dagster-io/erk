---
title: Creating a review
description: Add a new automated code review to your project
---

Reviews are markdown files in `.erk/reviews/`. Drop a file, and the CI workflow picks it up automatically — no workflow edits needed.

## Before you start

Check whether an existing review already covers your quality dimension. If a review targets the same files with the same tools and checks a related concern, extend it with an additional step rather than creating a new file. Create a new review when the concern is distinct (different model, different file patterns, or fundamentally different analysis).

## The review file

A minimal review file:

```markdown
---
name: Import Hygiene
paths:
  - "src/**/*.py"
marker: "<!-- import-hygiene-review -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Identify Changed Files

Run `gh pr diff` and extract files matching `src/**/*.py`.

## Step 2: Check Import Patterns

For each file, verify:
- No relative imports (`from .module import X`)
- No `import *` statements
- No import-time side effects beyond static constants

## Step 3: Post Inline Comments

For each violation:
**Import Hygiene**: [what was detected] - [which rule]

## Step 4: Summary Comment

### Files Reviewed
- `file.py`: N issues
```

### Frontmatter fields

| Field | Description |
|-------|-------------|
| `name` | Display name shown in CI logs and PR comments |
| `paths` | Glob patterns matching files this review cares about. The discovery step skips reviews that don't match any changed file. |
| `marker` | HTML comment used for deduplication. The review updates its own summary comment rather than posting duplicates. |
| `model` | Which Claude model runs the review. See [model selection](#model-selection). |
| `timeout_minutes` | Maximum runtime before the CI job is killed |
| `allowed_tools` | Tool permissions granted to the model during the review |
| `enabled` | Set to `false` to disable without deleting |

## Writing review instructions

Structure each review as numbered steps (`## Step 1: [Action Verb + Object]`). The CI harness handles fetching the diff, deduplicating comments, and posting to the PR — your instructions focus on what to analyze and what constitutes a violation.

Use explicit classification taxonomies. Tell the model exactly what categories exist and how to sort findings into them.

**Good:**

```markdown
Classify each code block as:
- VERBATIM: Copies source code that will go stale
- CONCEPTUAL: Illustrates a pattern without copying implementation
- TEMPLATE: Provides a starting point the reader modifies
```

**Bad:**

```markdown
Check if code blocks look like they might be copied from source files.
```

The first version gives the model a decision tree. The second relies on vibes.

## Model selection

| Choose | When |
|--------|------|
| Haiku | The check is mechanical — pattern matching, file existence, line counting. Fast and cheap. |
| Sonnet | The check requires judgment — reading documentation, weighing exceptions, cross-referencing source against prose. |

Start with Haiku. Upgrade to Sonnet only if you find the model missing violations that require contextual reasoning.

## Testing your review

Run your review locally before relying on CI:

```bash
erk exec run-review --name import-hygiene --local    # Run against current changes
erk exec run-review --name import-hygiene --dry-run   # Preview the prompt without executing
```

**Verification checklist:**

1. `--dry-run` shows the expected prompt with your steps and the correct file patterns.
2. `--local` runs against a real diff and produces accurate inline comments.
3. Push to a draft PR and confirm the review appears in the CI matrix and posts comments correctly.

## Related

- [Code reviews](/concepts/01-code-reviews/) — model selection rationale and the two-phase pattern
- [Addressing review feedback](/guides/01-addressing-review-feedback/) — how review comments get resolved

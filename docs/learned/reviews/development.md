---
title: Review Development Guide
read_when:
  - creating a new code review for CI
  - adding a new review spec to .github/reviews/
  - understanding the end-to-end review creation process
tripwires:
  - action: "creating a new review without checking if existing reviews can be extended"
    warning: "Before creating a new review, check if an existing review type can handle the new checks. See the review types taxonomy for the decision framework."
  - action: "creating a separate GitHub Actions workflow file for a new review"
    warning: "Reviews use convention-based discovery from a single workflow. Drop a markdown file in .github/reviews/ — do NOT create a new .yml workflow."
---

# Review Development Guide

Erk uses a convention-based review system: a single GitHub Actions workflow discovers and runs review specs defined as markdown files. Creating a new review means writing a markdown file, not a workflow file.

## Why Convention-Based (Not Per-Workflow)

Early reviews each had their own `.github/workflows/review-<name>.yml`. This created maintenance problems: duplicated setup steps, inconsistent boilerplate, and no centralized control over tool permissions or timeout defaults.

<!-- Source: .github/workflows/code-reviews.yml -->

The current system uses one workflow (`code-reviews.yml`) that discovers all `*.md` files in `.github/reviews/`, parses their frontmatter, matches their `paths` patterns against PR changed files, and runs matching reviews as parallel matrix jobs. Adding a review means dropping a markdown file — the workflow handles discovery, path matching, prompt assembly, and Claude invocation automatically.

<!-- Source: src/erk/review/parsing.py, discover_matching_reviews -->
<!-- Source: src/erk/review/prompt_assembly.py, assemble_review_prompt -->

## The Five-Place Pattern

Creating a new review touches up to five places. Understanding why each exists prevents partial implementations.

| Place | What goes here | Why it's separate |
|-------|---------------|-------------------|
| `.github/reviews/<name>.md` | Review spec (frontmatter + step-by-step instructions) | Convention-based discovery reads this directory |
| Review spec frontmatter | `paths`, `marker`, `model`, `allowed_tools` | Controls when the review triggers and what tools the agent can use |
| Review spec body | Numbered steps the agent executes | Each review has unique analysis logic |
| `docs/learned/reviews/<name>.md` | Cross-cutting insights about this review | Only if the review has non-obvious behavior worth documenting |
| `docs/learned/reviews/index.md` | Auto-generated via `erk docs sync` | Frontmatter `read_when` drives the index entry |

**The first three are mandatory. The last two are only needed if the review has cross-cutting insights** that don't fit in the spec itself (most reviews don't need a separate learned doc).

## Pre-Creation Decision: Extend or Create?

This is the most important decision. Creating overlapping reviews wastes CI time and confuses failure attribution.

<!-- Source: docs/learned/ci/review-types-taxonomy.md -->

See `docs/learned/ci/review-types-taxonomy.md` for the full three-dimensional decision framework (quality dimension, file scope, tools). The quick test:

| Signal | Action |
|--------|--------|
| Same quality dimension + same files + same tools | Extend existing review |
| New quality dimension OR new file scope OR different tools | Create new review |
| Same dimension but different performance profiles (fast vs slow) | Create new review |

## Writing the Review Spec

### Frontmatter Requirements

<!-- Source: src/erk/review/parsing.py, validate_review_frontmatter -->
<!-- Source: docs/learned/ci/review-spec-format.md -->

See `validate_review_frontmatter()` in `src/erk/review/parsing.py` for required and optional fields with their defaults. See `docs/learned/ci/review-spec-format.md` for the design rationale behind the spec format.

Key decisions when writing frontmatter:

- **`paths`**: Be specific — overly broad patterns (e.g., `**/*`) cause unnecessary review runs on unrelated PRs
- **`marker`**: Must be a unique HTML comment. The prompt assembly system uses this for summary comment identification and activity log preservation
- **`allowed_tools`**: Security boundary. Most reviews only need `Read(*)` and `Bash(gh:*)`. Don't grant `Write` or `Bash(*)` unless the review needs to modify files
- **`model`**: Default to `claude-haiku-4-5` for cost efficiency. Only escalate to sonnet for reviews requiring deep reasoning

### Body Structure: Numbered Steps

Review bodies must use numbered steps (`## Step 1: [Action Verb + Object]`) because the prompt assembly system wraps them with additional boilerplate steps (fetching the diff, checking for duplicate comments, posting summary).

<!-- Source: src/erk/review/prompt_assembly.py, REVIEW_PROMPT_TEMPLATE -->

See `REVIEW_PROMPT_TEMPLATE` in `src/erk/review/prompt_assembly.py` for the boilerplate that wraps your spec. Your spec's steps become "Step 1: Review-Specific Instructions" inside a larger prompt that handles diff retrieval, deduplication, inline comment posting, and summary updates.

**This means your spec should NOT include steps for:**

- Fetching the diff (the template does this)
- Posting inline comments (the template provides the `erk exec` commands)
- Posting/updating the summary comment (the template handles this)

**Your spec should focus on:**

- What standards to load (Step 1: Load rules)
- How to analyze the diff (Step 2: Classify changes)
- What constitutes a violation vs a pass (explicit taxonomy)
- Inline comment format for violations

### Classification Taxonomies Over Prose

Reviews with explicit classification taxonomies produce better results than reviews with general guidance. Compare:

**WRONG**: "Analyze each file and flag issues"

**RIGHT**: Explicit categories with actions:
- Category A (thin CLI wrapper): Skip — only Click decorators
- Category B (new source with logic): Flag — needs test coverage
- Category C (type-only file): Skip — no runtime behavior

This makes activity logs meaningful ("3 thin CLI wrappers skipped, 1 source file flagged") and reduces false positives.

## Testing a New Review

### Local Testing

Use `erk exec run-review --name <name> --local --dry-run` to preview the assembled prompt without running Claude. This verifies your spec parses correctly and the prompt reads coherently.

<!-- Source: src/erk/cli/commands/exec/scripts/run_review.py, run_review -->

Then `--local` (without `--dry-run`) runs the review against local changes vs the trunk branch. This is faster than pushing a PR but doesn't test the GitHub comment posting path.

### CI Testing

Push a branch with changes that should trigger the review. Verify:

1. The discovery job finds your review (check the "Discover matching reviews" step output)
2. The review job runs with your spec
3. Inline comments land on the correct lines
4. The summary comment uses your marker and formats correctly
5. The review does NOT run when only unrelated files change (push a docs-only change and confirm it's skipped)

## Anti-Patterns

### Creating a Separate Workflow File

**WRONG**: Creating `.github/workflows/review-my-check.yml`

The convention-based system exists precisely to avoid per-review workflow files. Drop a markdown file in `.github/reviews/` and the single `code-reviews.yml` workflow handles the rest.

### Assuming Write Access

**WRONG**: Writing a review spec that modifies files

Reviews are read-only analysis. The `allowed_tools` frontmatter field enforces this — most reviews use `Read(*)` and `Bash(gh:*)` only. If your review needs to modify files, it's not a review — it's a linter or formatter that belongs in a different CI job.

### Vague Step Descriptions

**WRONG**: `## Step 1: Setup`

**RIGHT**: `## Step 1: Load Dignified Python Standards`

Agents need action verbs and specific objects, not abstract phase names.

## Related Documentation

- [Review Types Taxonomy](../ci/review-types-taxonomy.md) — Decision framework for extend-vs-create
- [Review Spec Format](../ci/review-spec-format.md) — Design rationale behind spec structure
- Existing review specs in `.github/reviews/` — Reference implementations

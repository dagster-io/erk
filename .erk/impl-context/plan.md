# Plan: Code Reviews Documentation for docs-v2

## Context

The docs-v2 site (Astro Starlight) has placeholder content. The first real section to write covers erk's code review subsystem. The user wants three documents: a conceptual introduction, a guide for the pr-address workflow, and a guide for adding new reviews.

## Step 0: Remove placeholder content

Delete all existing placeholder files so the site only shows real content:

- `docs-v2/src/content/docs/getting-started/01-introduction.md`
- `docs-v2/src/content/docs/concepts/01-plan-oriented-engineering.md`
- `docs-v2/src/content/docs/guides/01-local-workflow.md`
- `docs-v2/src/content/docs/reference/01-cli.md`

Update `docs-v2/src/content/docs/index.mdx` to redirect to the first real page (`/concepts/01-code-reviews/`) instead of the deleted introduction.

Remove empty sidebar sections from `docs-v2/astro.config.mjs` — keep only `Concepts` and `Guides` (since Getting Started and Reference have no content).

## Document 1: `concepts/01-code-reviews.md`

**Title**: Code reviews
**Description**: How erk uses tiered AI models to review and resolve PR feedback

Sections:

- **The two-phase pattern**: Phase 1 is CI-based detection — cheap models (Haiku) run mechanical checks (style, test coverage, simplification), Sonnet handles judgment-heavy reviews (tripwires, doc audits). Each review posts inline comments + summary on the PR. Phase 2 is human-steered resolution — a human reviews flagged issues, then triggers pr-address where a powerful model classifies, batches, and resolves comments under human oversight.
- **Convention-based discovery**: Reviews are markdown files in `.erk/reviews/`. A single GitHub Actions workflow discovers matching reviews by file patterns and runs them as parallel matrix jobs. Adding a review = dropping a markdown file.
- **Model selection**: Table of the five existing reviews mapped to their models with one-line rationale (Haiku for mechanical, Sonnet for judgment, powerful model for resolution).
- **What reviews check**: One-sentence inventory of the five reviews (test coverage, dignified-python, tripwires, doc audit, code simplifier).
- **What's next**: Links to the two guides.

Target length: ~350 words. Conceptual, not procedural.

## Document 2: `guides/01-addressing-review-feedback.md`

**Title**: Addressing review feedback
**Description**: Resolve PR review comments using the pr-address workflow

Sections:

- **Running pr-address**: Show `/erk:pr-address`, `--pr` variant, and the preview command.
- **How classification works**: Haiku subagent classifies each comment as actionable vs informational, assigns complexity (local, single-file, cross-cutting, complex), detects pre-existing issues in moved code. Comments are grouped into ordered batches.
- **The batching model**: Batch 0 = pre-existing (auto-resolve), Batch 1-2 = local/single-file (auto-proceed), Batch 3-4 = cross-cutting/complex (user approval required), Batch 5 = informational (user decides act/dismiss).
- **What happens in each batch**: Address → CI → commit → resolve threads → report. Mention false positive handling.
- **After all batches complete**: Final verification, PR description update, push instructions.
Target length: ~500 words. Workflow-oriented with concrete commands.

## Document 3: `guides/02-creating-a-review.md`

**Title**: Creating a review
**Description**: Add a new automated code review to your project

Sections:

- **Before you start**: Decide extend vs create (same quality dimension + files + tools → extend).
- **The review file**: Show a minimal complete example with frontmatter + body. Explain each frontmatter field in one line: name, paths, marker, model, timeout_minutes, allowed_tools, enabled.
- **Writing review instructions**: Numbered steps (`## Step 1: [Action Verb + Object]`). Your spec focuses on what to analyze and what's a violation — boilerplate handles diff, dedup, posting. Use explicit classification taxonomies, not vague prose. Show good vs bad example.
- **Model selection**: Haiku for mechanical, Sonnet for judgment. Cost/speed trade-off.
- **Testing your review**: `--dry-run` to preview prompt, `--local` to run against current changes, CI verification checklist.

Target length: ~450 words. Procedural — reader can create a working review by following along.

## Cross-references

- Concept page links forward to both guides in "What's next"
- Addressing guide links back to concept and forward to creating guide
- Creating guide links back to concept for model rationale
- Use Starlight relative paths: `/concepts/01-code-reviews/`, `/guides/01-addressing-review-feedback/`, `/guides/02-creating-a-review/`

## Style

Follow STYLE-GUIDE.md: direct, second person, active voice, present tense, no hedge words. Use terminology table (plan, worktree, land). Code examples first, then explanation.

## Verification

1. Run `cd docs-v2 && npm run build` to confirm Starlight compiles with new pages
2. Run `npm run dev` and verify pages appear in sidebar under Concepts and Guides with correct ordering
3. Confirm cross-reference links resolve

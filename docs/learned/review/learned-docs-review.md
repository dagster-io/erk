---
title: Learned Docs Review
read_when:
  - understanding how documentation quality is enforced at PR time
  - debugging why a PR received verbatim code comments
  - adding or modifying the audit-pr-docs review
tripwires:
  - action: "adding code blocks longer than 5 lines to docs/learned/ files"
    warning: "Verbatim source code will go stale. Use source pointers instead. See docs/learned/documentation/source-pointers.md."
---

# Learned Docs Review

The `audit-pr-docs` review is the PR-time enforcement layer of erk's documentation quality system. It prevents new problems from merging by detecting verbatim source code, inaccurate claims, and duplicative content in `docs/learned/` files. The other two layers — `/local:audit-doc` (deep single-doc analysis) and `/local:audit-scan` (triage across all docs) — clean up existing problems. Together the three form a closed loop described in [stale-code-blocks-are-silent-bugs.md](../documentation/stale-code-blocks-are-silent-bugs.md).

## Why a Separate Review Rather Than Linting

A linter could catch `from erk` imports in code blocks, but the classification problem is harder than pattern matching. The review must distinguish between:

| Classification    | Example                                      | Action         |
| ----------------- | -------------------------------------------- | -------------- |
| **VERBATIM**      | Copied gateway method with real class names  | Flag           |
| **ANTI-PATTERN**  | Code marked WRONG showing what not to do     | Skip (allowed) |
| **CONCEPTUAL**    | Made-up names (`MyGateway`, `ExampleWidget`) | Skip (allowed) |
| **TEMPLATE**      | Third-party API usage (Click, pytest, Rich)  | Skip (allowed) |
| **Short snippet** | ≤5 lines showing a key insight               | Skip (allowed) |

This classification requires judgment about intent and context — whether a block teaches an external API, demonstrates an anti-pattern, or copies real implementation code. An AI review agent handles the ambiguous middle ground that regex-based linting cannot.

## Audit-on-Touch: Full Document, Not Just Diff

<!-- Source: .github/reviews/audit-pr-docs.md, Step 2: Identify Changed Doc Files -->

The review audits the **entire document** whenever any part of it is modified, not just the changed lines from the diff. This is a deliberate design choice: when someone is actively editing a doc is the cheapest time to fix pre-existing problems. A surgical diff-only scan would miss stale code blocks that were already present.

## Analysis Is Delegated, Not Duplicated

<!-- Source: .github/reviews/audit-pr-docs.md, Step 3: Audit Each Changed Doc -->

The review spec itself contains no analysis methodology — it delegates entirely to `/local:audit-doc` for the classification framework, verification ordering, and verdict thresholds (KEEP, SIMPLIFY, REPLACE WITH CODE REFS, CONSIDER DELETING). This avoids maintaining parallel analysis logic in two places. The review spec only defines the review-specific mechanics: diff filtering, PR comment format, and activity log structure.

**Anti-pattern**: Adding classification logic directly to the review spec. If you need to change how code blocks are classified, change it in `audit-doc` — the review spec inherits it automatically.

## Prompt-Embedded Dedup Prevents Comment Floods

Reviews run on every push to a PR. Without deduplication, each iteration would re-post the same violations. The dedup system is prompt-embedded (not code-enforced) — the review agent is instructed to fetch existing comments and skip near-matches using an 80-character body prefix and ±2-line proximity window. For the full rationale behind this design, see [inline-comment-deduplication.md](inline-comment-deduplication.md).

## Integration with the Convention-Based Review System

<!-- Source: src/erk/review/prompt_assembly.py, REVIEW_PROMPT_TEMPLATE -->
<!-- Source: src/erk/review/parsing.py, discover_matching_reviews -->

`audit-pr-docs` is one of several reviews in `.github/reviews/`. All reviews share the same infrastructure: YAML frontmatter defines scope and model, `discover-reviews` matches changed files to review definitions, and `run-review` assembles the prompt and invokes Claude. Adding a new review requires only dropping a markdown file in `.github/reviews/` — see [convention-based-reviews.md](../ci/convention-based-reviews.md) for the full system.

The `audit-pr-docs` review uses `claude-haiku-4-5` because its task is mechanical extraction and classification, not creative analysis. Faster model = faster CI feedback.

## Related Documentation

- [inline-comment-deduplication.md](inline-comment-deduplication.md) — Dedup design and matching heuristics
- [convention-based-reviews.md](../ci/convention-based-reviews.md) — Shared review infrastructure
- [source-pointers.md](../documentation/source-pointers.md) — Replacement format for verbatim code blocks
- [stale-code-blocks-are-silent-bugs.md](../documentation/stale-code-blocks-are-silent-bugs.md) — Why embedded source code is treated as a defect
- [audit-methodology.md](../documentation/audit-methodology.md) — Classification framework used by the review

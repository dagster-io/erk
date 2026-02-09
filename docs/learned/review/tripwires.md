---
title: Review Tripwires
read_when:
  - "working on review code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from review/*.md frontmatter -->

# Review Tripwires

Rules triggered by matching actions in code.

**adding a new review mode without updating assemble_review_prompt validation** → Read [Review Prompt Assembly](prompt-assembly.md) first. The function validates mutual exclusivity of pr_number and base_branch. New modes must fit within or extend this validation.

**adding code blocks longer than 5 lines to docs/learned/ files** → Read [Learned Docs Review](learned-docs-review.md) first. Verbatim source code will go stale. Use source pointers instead. See docs/learned/documentation/source-pointers.md.

**posting inline review comments without deduplication** → Read [Inline Comment Deduplication](inline-comment-deduplication.md) first. Always deduplicate before posting. The dedup logic is prompt-embedded, not code-enforced — see Step 4 of REVIEW_PROMPT_TEMPLATE.

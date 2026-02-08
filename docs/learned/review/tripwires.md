---
title: Review Tripwires
read_when:
  - "working on review code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from review/*.md frontmatter -->

# Review Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding a new review mode without updating assemble_review_prompt validation** → Read [Review Prompt Assembly](prompt-assembly.md) first. The function validates mutual exclusivity of pr_number and base_branch. New modes must fit within or extend this validation.

**CRITICAL: Before adding code blocks longer than 5 lines to docs/learned/ files** → Read [Learned Docs Review](learned-docs-review.md) first. Verbatim source code will go stale. Use source pointers or short illustrative snippets instead. See learned-docs skill for guidance.

**CRITICAL: Before posting inline review comments without deduplication** → Read [Inline Comment Deduplication](inline-comment-deduplication.md) first. Always deduplicate before posting. Use (path, line, body_prefix) key with 80-char prefix and 2-line proximity tolerance.
